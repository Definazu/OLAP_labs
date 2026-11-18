"""Load validated CSV into a star schema and publish the same rows to ClickHouse."""

import argparse
import csv
from decimal import Decimal
import fcntl
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import duckdb


ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / 'sql'
RUN = ROOT / '.run'
SCHEMA = 'retail_mart'
STAGE = 'retail_mart_stage'
TABLES = ('dim_store', 'dim_date', 'dim_product', 'fact_sales')
SOURCES = {
    'store': ('dim_store.csv', dict(store_id='UINTEGER', store_name='VARCHAR', city='VARCHAR', region='VARCHAR')),
    'product': ('dim_product.csv', dict(product_id='UINTEGER', product_name='VARCHAR', category='VARCHAR', brand='VARCHAR')),
    'date': ('dim_date.csv', dict(date_id='UINTEGER', full_date='DATE', year='USMALLINT', month='UTINYINT',
                                 month_name='VARCHAR', day_of_week='UTINYINT')),
    'sales': ('fact_sales.csv', dict(sale_id='UBIGINT', date_id='UINTEGER', store_id='UINTEGER',
                                    product_id='UINTEGER', qty='INTEGER', amount='VARCHAR')),
    'changes': ('product_category_changes.csv', dict(product_id='UINTEGER', effective_date='DATE', category='VARCHAR')),
}


def read_sql(name):
    return (SQL / name).read_text(encoding='utf-8')


def load_duckdb(connection, raw_dir):
    for name, (filename, columns) in SOURCES.items():
        path = raw_dir / filename
        with path.open(encoding='utf-8-sig', newline='') as source:
            if next(csv.reader(source), None) != list(columns):
                raise ValueError(f'{filename}: unexpected CSV header; expected {list(columns)}')
        column_types = ', '.join(f"'{key}': '{value}'" for key, value in columns.items())
        connection.execute(
            f'CREATE TEMP TABLE raw_{name} AS SELECT * FROM read_csv('
            f"?, columns={{{column_types}}}, header=true, auto_detect=false, delim=',', strict_mode=true)",
            [str(path)],
        )

    checks = connection.execute(read_sql('quality.sql')).fetchall()
    for name, violations in checks:
        print(f'quality: {name} = {violations}', flush=True)
    if any(violations for _, violations in checks):
        raise ValueError('quality checks failed; warehouse was not changed')

    print(f'raw: positions={connection.execute("SELECT COUNT(*) FROM raw_sales").fetchone()[0]}', flush=True)
    connection.execute('BEGIN TRANSACTION')
    try:
        connection.execute(read_sql('ddl_duckdb.sql'))
        connection.execute(read_sql('transform_duckdb.sql'))
        connection.execute('COMMIT')
    except Exception:
        connection.execute('ROLLBACK')
        raise


def clickhouse(query, csv_path=None):
    command = ['docker', 'compose', 'exec', '-T', 'clickhouse', 'clickhouse-client']
    if csv_path is None:
        result = subprocess.run(command + ['--multiquery', '--query', query], cwd=ROOT,
                                check=True, capture_output=True, text=True, encoding='utf-8')
        return result.stdout.strip()
    with csv_path.open('rb') as source:
        subprocess.run(command + ['--query', query], cwd=ROOT, stdin=source, check=True)


def totals_sql(schema):
    counts = '\nUNION ALL\n'.join(
        f"SELECT '{table}' AS table_name, COUNT(*) AS row_count FROM {schema}.{table}" for table in TABLES
    )
    return f'SELECT table_name, row_count FROM ({counts}) AS counts ORDER BY table_name'


def publish_clickhouse(connection, totals, turnover):
    ddl = read_sql('ddl_clickhouse.sql')
    aggregate_ddl, aggregate_insert = read_sql('aggregate_clickhouse.sql').split(';', maxsplit=1)
    clickhouse(f'CREATE DATABASE IF NOT EXISTS {SCHEMA} ENGINE = Atomic')
    clickhouse(ddl.format(schema=SCHEMA))
    clickhouse(aggregate_ddl.format(schema=SCHEMA))
    clickhouse(f'DROP DATABASE IF EXISTS {STAGE} SYNC; CREATE DATABASE {STAGE} ENGINE = Atomic')

    with TemporaryDirectory() as temporary:
        clickhouse(ddl.format(schema=STAGE))
        for table in TABLES:
            export = Path(temporary) / f'{table}.csv'
            connection.execute(
                f"COPY {SCHEMA}.{table} TO ? (FORMAT CSV, HEADER true, NULL '\\N')", [str(export)]
            )
            clickhouse(f'INSERT INTO {STAGE}.{table} FORMAT CSVWithNames', export)

    clickhouse(aggregate_ddl.format(schema=STAGE) + ';' + aggregate_insert.format(schema=STAGE))
    stage_counts = [(name, int(count)) for name, count in
                    (row.split('\t') for row in clickhouse(totals_sql(STAGE)).splitlines())]
    stage_turnover = Decimal(clickhouse(read_sql('canonical_metric.sql').replace(SCHEMA, STAGE)))
    if stage_counts != totals or turnover != stage_turnover:
        raise ValueError(f'ClickHouse staging differs from DuckDB: {stage_counts}, turnover={stage_turnover}')

    exchanged = []
    try:
        for table in (*TABLES, 'agg_daily_store'):
            clickhouse(f'EXCHANGE TABLES {SCHEMA}.{table} AND {STAGE}.{table}')
            exchanged.append(table)
    except Exception:
        for table in reversed(exchanged):
            clickhouse(f'EXCHANGE TABLES {SCHEMA}.{table} AND {STAGE}.{table}')
        raise

    clickhouse(f'DROP DATABASE {STAGE} SYNC')
    clickhouse('CREATE USER IF NOT EXISTS olap_bi IDENTIFIED WITH no_password; '
               f'GRANT SELECT ON {SCHEMA}.* TO olap_bi')
    print(f'ClickHouse: {dict(stage_counts)}, turnover={stage_turnover:.2f}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duckdb-only', action='store_true')
    parser.add_argument('--raw-dir', type=Path, default=ROOT / 'data' / 'raw')
    parser.add_argument('--duckdb-file', type=Path, default=RUN / 'retail.duckdb')
    args = parser.parse_args()
    RUN.mkdir(exist_ok=True)
    args.duckdb_file.parent.mkdir(parents=True, exist_ok=True)
    with (RUN / 'load.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with duckdb.connect(str(args.duckdb_file)) as connection:
            load_duckdb(connection, args.raw_dir)
            totals = connection.execute(totals_sql(SCHEMA)).fetchall()
            turnover = connection.execute(read_sql('canonical_metric.sql')).fetchone()[0]
            print(f'DuckDB: {dict(totals)}, turnover={turnover:.2f}', flush=True)
            if not args.duckdb_only:
                publish_clickhouse(connection, totals, turnover)


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(f'ClickHouse command failed ({error.returncode}): {error.stderr or "see client output"}', file=sys.stderr)
        sys.exit(1)
    except (ValueError, duckdb.Error, OSError) as error:
        print(f'Load failed: {error}', file=sys.stderr)
        sys.exit(1)
