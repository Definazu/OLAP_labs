# Дашборд Metabase

«Оборот розничной сети · I квартал 2024». Подключение `clickhouse:8123` из контейнера Metabase к базе `retail_mart`. Учётная запись `olap_bi` читает опубликованные таблицы витрины.

| Карточка | Источник | SQL |
|---|---|---|
| Оборот сети | `fact_sales`, `dim_date` | [turnover.sql](turnover.sql) |
| Оборот по месяцам | `agg_daily_store`, `dim_date` | [monthly.sql](monthly.sql) |
| Оборот по категориям | `fact_sales`, `dim_product` SCD2 | [categories.sql](categories.sql) |
| Три магазина с наибольшим оборотом | `fact_sales`, `dim_store` | [stores.sql](stores.sql) |

«Регион» действует на все четыре карточки. Без выбора используется весь квартал по сети. Каждый SQL-вопрос использует фильтр Metabase, связанный с `dim_store.region`. На главной карточке сохранена формула и границы периода эталона из `sql/canonical_metric.sql`, а условие по региону добавляется при выборе значения.

Команда `python dashboards/setup.py` создаёт панель и прогоняет запросы карточек через API Metabase без фильтра и с каждым регионом. Ссылка на панель появляется в выводе команды. В сериях без наблюдений точки отсутствуют. Сумма на карточке топ-3 относится только к трём показанным магазинам.

[Панель по всем регионам](../evidence/dashboard.png) · [Панель с фильтром «Запад»](../evidence/dashboard-west.png)

В этой версии Metabase драйвер ClickHouse включён. [Документация Metabase по ClickHouse](https://www.metabase.com/docs/latest/databases/connections/clickhouse)
