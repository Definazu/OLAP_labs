"""Configure the local Metabase dashboard and verify the region filter via the API."""

from decimal import Decimal
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID, uuid5


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / '.run'
LOGIN = RUN / 'metabase-login.json'
URL = 'http://127.0.0.1:3000'
DATABASE = 'Розничная витрина · ClickHouse'
DASHBOARD = 'Оборот розничной сети · I квартал 2024'
REGION_ID = '090b497e-bd2a-41f7-ae8c-cd8529db68f0'
PARAMETER_TYPE = 'string/='
REGION_TARGET = ['dimension', ['template-tag', 'region']]
CARDS = (
    ('turnover', 'Оборот сети', 'scalar', None, (0, 0, 10, 6)),
    ('monthly', 'Оборот по месяцам', 'line', 'sale_month', (0, 10, 14, 6)),
    ('categories', 'Оборот по категориям', 'row', 'category', (6, 0, 12, 9)),
    ('stores', 'Три магазина с наибольшим оборотом', 'row', 'store', (6, 12, 12, 9)),
)


class Metabase:
    def __init__(self):
        self.headers = {'Content-Type': 'application/json'}

    def request(self, method, path, body=None):
        payload = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        try:
            with urlopen(Request(URL + '/api' + path, data=payload, headers=self.headers, method=method), timeout=60) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except HTTPError as error:
            details = error.read().decode(errors='replace')
            if path in ('/setup', '/session'):
                details = 'check local Metabase initialization and credentials'
            raise RuntimeError(f'{method} {path}: HTTP {error.code}: {details}') from None

    def get(self, path):
        return self.request('GET', path)


def wait_for(action, description):
    end = time.monotonic() + 240
    while time.monotonic() < end:
        try:
            result = action()
            if result:
                return result
        except (URLError, ConnectionError, TimeoutError, RuntimeError):
            pass
        time.sleep(3)
    raise RuntimeError(f'Timed out waiting for {description}')


def authenticate(mb):
    wait_for(lambda: mb.get('/health')['status'] == 'ok', 'Metabase health')
    token = mb.get('/session/properties').get('setup-token')
    if LOGIN.exists():
        credentials = json.loads(LOGIN.read_text(encoding='utf-8'))
        try:
            session = mb.request('POST', '/session', credentials)
        except RuntimeError:
            if not token:
                raise
        else:
            mb.headers['X-Metabase-Session'] = session['id']
            return
    elif token:
        credentials = {'username': 'olap-admin@example.local', 'password': secrets.token_urlsafe(24)}
        with os.fdopen(os.open(LOGIN, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w', encoding='utf-8') as file:
            json.dump(credentials, file, indent=2)
    else:
        raise RuntimeError(f'Enter the existing Metabase admin username and password in {LOGIN}')

    if token:
        mb.request('POST', '/setup', {
            'token': token,
            'user': {'first_name': 'Глеб', 'last_name': 'Шадура',
                     'email': credentials['username'], 'password': credentials['password'],
                     'site_name': 'Практикум OLAP'},
            'prefs': {'site_name': 'Практикум OLAP', 'allow_tracking': False, 'site_locale': 'ru'},
        })
    session = mb.request('POST', '/session', credentials)
    mb.headers['X-Metabase-Session'] = session['id']


def get_database(mb):
    existing = next((db for db in mb.get('/database')['data'] if db['name'] == DATABASE), None)
    if existing:
        return existing['id']
    new = mb.request('POST', '/database', {
        'name': DATABASE, 'engine': 'clickhouse', 'is_full_sync': True,
        'details': {'host': 'clickhouse', 'port': 8123, 'dbname': 'retail_mart',
                    'user': 'olap_bi', 'password': '', 'ssl': False},
    })
    return new['id']


def region_field(mb, database):
    def find_region():
        metadata = mb.get(f'/database/{database}/metadata')
        tables = {t['name']: t for t in metadata['tables'] if t['schema'] == 'retail_mart'}
        required = {'dim_store', 'dim_date', 'dim_product', 'fact_sales', 'agg_daily_store'}
        if required.issubset(tables):
            return next((f['id'] for f in tables['dim_store']['fields'] if f['name'] == 'region'), None)

    return wait_for(find_region, 'ClickHouse table and field synchronization')


def configure_dashboard(mb, database, field):
    existing = next((dash for dash in mb.get('/dashboard') if dash['name'] == DASHBOARD), None)
    existing = existing or mb.request('POST', '/dashboard', {
        'name': DASHBOARD,
        'description': 'Учебные продажи с 01.01.2024 по 31.03.2024. Оборот указан в денежных единицах источника.',
    })
    dashboard = existing['id']
    previous = {item['card_id']: item['id'] for item in mb.get(f'/dashboard/{dashboard}')['dashcards']}
    saved_cards = {card['name']: card['id'] for card in mb.get('/card')}
    dashcards = []
    for key, name, display, dimension, (row, col, size_x, size_y) in CARDS:
        settings = {'column_settings': {'["name","turnover"]': {'decimals': 2}}}
        if dimension:
            settings.update({'graph.dimensions': [dimension], 'graph.metrics': ['turnover'],
                             'graph.y_axis.title_text': 'Оборот, ден. ед.', 'graph.x_axis.title_text': ''})
        body = {
            'name': name, 'display': display, 'visualization_settings': settings,
            'dataset_query': {'type': 'native', 'database': database, 'native': {
                'query': (ROOT / 'dashboards' / (key + '.sql')).read_text(encoding='utf-8').strip(),
                'template-tags': {'region': {'id': str(uuid5(UUID(REGION_ID), key)), 'name': 'region',
                                             'display-name': 'Регион', 'type': 'dimension',
                                             'dimension': ['field', field, None], 'widget-type': PARAMETER_TYPE}},
            }},
        }
        existing_id = saved_cards.get(name)
        card = mb.request('PUT', f'/card/{existing_id}', body) if existing_id else mb.request('POST', '/card', body)
        card_id = card['id']
        dashcards.append({'id': previous.get(card_id, -len(dashcards) - 1), 'card_id': card_id,
                          'row': row, 'col': col, 'size_x': size_x, 'size_y': size_y,
                          'parameter_mappings': [{'parameter_id': REGION_ID, 'card_id': card_id,
                                                  'target': REGION_TARGET}]})

    mb.request('PUT', f'/dashboard/{dashboard}', {
        'parameters': [{'id': REGION_ID, 'name': 'Регион', 'slug': 'region', 'type': PARAMETER_TYPE,
                        'values_source_type': 'static-list',
                        'values_source_config': {'values': ['Запад', 'Центр']}, 'isMultiSelect': False}],
        'dashcards': dashcards,
    })
    return mb.get(f'/dashboard/{dashboard}')


def verify_dashboard(mb, dashboard):
    with (ROOT / 'sql' / 'reconcile_regions.sql').open(encoding='utf-8') as sql:
        result = subprocess.run(['docker', 'compose', 'exec', '-T', 'clickhouse', 'clickhouse-client'],
                                cwd=ROOT, stdin=sql, capture_output=True, text=True, encoding='utf-8', check=True)
    expected = {scope: Decimal(turnover) for scope, _, turnover in
                (line.split('\t') for line in result.stdout.splitlines())}
    dashboard_id = dashboard['id']
    for item in sorted(dashboard['dashcards'], key=lambda card: (card['row'], card['col'])):
        endpoint = f'/dashboard/{dashboard_id}/dashcard/{item["id"]}/card/{item["card_id"]}/query'
        for region in (None, 'Запад', 'Центр'):
            parameters = [{'id': REGION_ID, 'type': PARAMETER_TYPE, 'value': [region],
                           'target': REGION_TARGET}] if region else []
            result = mb.request('POST', endpoint, {'parameters': parameters, 'ignore_cache': True})
            if result['status'] != 'completed':
                raise RuntimeError(f'Card {item["card"]["name"]}: {result}')
            rows = result['data']['rows']
            name = item['card']['name']
            if not rows:
                raise RuntimeError(f'Card {name}: no rows for {region}')
            turnover = sum(Decimal(str(row[-1])) for row in rows)
            scope = region or 'Все регионы'
            if name != CARDS[-1][1] and turnover != expected[scope]:
                raise RuntimeError(f'{name}, {scope}: Metabase {turnover} differs from SQL {expected[scope]}')
            print(f'{name} | {scope} | rows={len(rows)} | sum={turnover:.2f}', flush=True)


def main():
    RUN.mkdir(exist_ok=True)
    mb = Metabase()
    authenticate(mb)
    database = get_database(mb)
    dashboard = configure_dashboard(mb, database, region_field(mb, database))
    verify_dashboard(mb, dashboard)
    print(f'{URL}/dashboard/{dashboard["id"]}', flush=True)


if __name__ == '__main__':
    main()
