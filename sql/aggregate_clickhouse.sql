CREATE TABLE IF NOT EXISTS {schema}.agg_daily_store (
    date_id UInt32,
    store_id UInt32,
    turnover Decimal(38, 2)
) ENGINE = MergeTree
PARTITION BY intDiv(date_id, 100)
ORDER BY (date_id, store_id);

INSERT INTO {schema}.agg_daily_store
SELECT date_id, store_id, sum(amount) AS turnover
FROM {schema}.fact_sales
GROUP BY date_id, store_id;
