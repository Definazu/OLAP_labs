CREATE TABLE IF NOT EXISTS {schema}.dim_store (
    store_id UInt32,
    store_name String,
    city String,
    region LowCardinality(String)
) ENGINE = MergeTree ORDER BY store_id;

CREATE TABLE IF NOT EXISTS {schema}.dim_product (
    product_sk UInt64,
    product_id UInt32,
    product_name String,
    category LowCardinality(String),
    brand String,
    valid_from Date,
    valid_to Nullable(Date),
    is_current Bool
) ENGINE = MergeTree ORDER BY (product_id, valid_from);

CREATE TABLE IF NOT EXISTS {schema}.dim_date (
    date_id UInt32,
    full_date Date,
    year UInt16,
    month UInt8,
    month_name String,
    day_of_week UInt8
) ENGINE = MergeTree ORDER BY date_id;

CREATE TABLE IF NOT EXISTS {schema}.fact_sales (
    sale_id UInt64,
    date_id UInt32,
    store_id UInt32,
    product_sk UInt64,
    qty Int32,
    amount Decimal(12, 2)
) ENGINE = MergeTree
PARTITION BY intDiv(date_id, 100)
ORDER BY (date_id, store_id, product_sk)
SETTINGS index_granularity = 8192;
