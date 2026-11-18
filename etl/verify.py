"""Reproduce the DuckDB/ClickHouse reconciliation and the SCD2 and rejection demos."""

import argparse
import csv
from decimal import Decimal
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

import duckdb

from load import ROOT, RUN, clickhouse, read_sql, totals_sql


def statements(name):
    return [sql.strip() for sql in read_sql(name).split(';') if sql.strip()]


def compare_engines(connection):
    queries = [totals_sql('retail_mart'), read_sql('canonical_metric.sql'), *statements('analytics.sql')]
    labels = ['counts', 'canonical metric', 'monthly stores', 'regional category rank', 'top 3 stores',
              'January West', 'monthly and yearly roll-up']
    for label, sql in zip(labels, queries, strict=True):
        duck_rows = connection.execute(sql).fetchall()
        ch_rows = [row.split('\t') for row in clickhouse(sql).splitlines()]
        if len(duck_rows) != len(ch_rows):
            raise AssertionError((label, duck_rows, ch_rows))
        for duck_row, ch_row in zip(duck_rows, ch_rows, strict=True):
            for expected, actual in zip(duck_row, ch_row, strict=True):
                if isinstance(expected, Decimal):
                    assert expected == Decimal(actual), (label, duck_row, ch_row)
                else:
                    assert str(expected) == actual, (label, duck_row, ch_row)
        print(f'{label}: DuckDB = ClickHouse ({len(duck_rows)} rows)')
        for row in duck_rows:
            print('  ' + ' | '.join(map(str, row)))

    aggregate = clickhouse('''
        WITH by_day AS (
            SELECT date_id, store_id, sum(amount) AS turnover
            FROM retail_mart.fact_sales GROUP BY date_id, store_id
        )
        SELECT count()
        FROM by_day AS f FULL OUTER JOIN retail_mart.agg_daily_store AS a USING (date_id, store_id)
        WHERE f.turnover IS NULL OR a.turnover IS NULL OR f.turnover != a.turnover
        SETTINGS join_use_nulls = 1
    ''')
    assert aggregate == '0', f'Daily aggregate mismatch: {aggregate}'
    print('daily aggregate: no differences at date_id × store_id grain')
    print(clickhouse('''
        SELECT intDiv(date_id, 100) AS month, sum(turnover) AS turnover
        FROM retail_mart.agg_daily_store GROUP BY month ORDER BY month
    '''))
    print('January filter vs store-only filter:')
    for sql in statements('primary_index_clickhouse.sql'):
        print(clickhouse(sql))


def simulate_scd_and_bad_input(connection):
    for sql in statements('scd2_demo.sql'):
        for row in connection.execute(sql).fetchall():
            print('  ' + ' | '.join(map(str, row)))

    products_in_january = '''
        SELECT p.category, SUM(f.amount)
        FROM retail_mart.fact_sales AS f JOIN retail_mart.dim_product AS p USING (product_sk)
        WHERE p.product_id = 101 AND f.date_id >= 20240101 AND f.date_id < 20240201
        GROUP BY p.category
    '''
    with TemporaryDirectory() as temp:
        temp = Path(temp)
        raw = temp / 'raw'
        shutil.copytree(ROOT / 'data' / 'raw', raw)
        (raw / 'product_category_changes.csv').write_text('product_id,effective_date,category\n', encoding='utf-8')
        baseline = temp / 'baseline.duckdb'
        command = [sys.executable, str(ROOT / 'etl' / 'load.py'), '--duckdb-only',
                   '--raw-dir', str(raw), '--duckdb-file', str(baseline)]
        subprocess.run(command, check=True, capture_output=True)
        with duckdb.connect(str(baseline), read_only=True) as before:
            before_rows = before.execute(products_in_january).fetchall()
        after_rows = connection.execute(products_in_january).fetchall()
        assert before_rows == after_rows == [('Молочка', Decimal('45.00'))]
        print(f'SCD2: January before and after the change: {after_rows[0][0]} | {after_rows[0][1]:.2f}')

        sales = raw / 'fact_sales.csv'
        samples = sales.read_text(encoding='utf-8').rstrip('\n')
        with sales.open('w', encoding='utf-8', newline='') as file:
            file.write(samples + '\n')
            csv.writer(file, lineterminator='\n').writerow((9000, 20240101, 99999, 101, 1, '1.00'))
        failed = subprocess.run(command, text=True, encoding='utf-8', capture_output=True)
        assert failed.returncode != 0 and 'missing references = 1' in failed.stdout, (failed.stdout, failed.stderr)
        print(f'bad store FK rejected (exit {failed.returncode}):')
        print(failed.stdout.rstrip())
        print(failed.stderr.rstrip())
        with duckdb.connect(str(baseline), read_only=True) as before:
            value = before.execute(read_sql('canonical_metric.sql')).fetchone()[0]
            assert value == connection.execute(read_sql('canonical_metric.sql')).fetchone()[0]
            print(f'previous snapshot retained: {value:.2f}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duckdb-only', action='store_true')
    args = parser.parse_args()
    with duckdb.connect(str(RUN / 'retail.duckdb'), read_only=True) as connection:
        if not args.duckdb_only:
            compare_engines(connection)
        simulate_scd_and_bad_input(connection)


if __name__ == '__main__':
    main()
