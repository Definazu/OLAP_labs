DROP SCHEMA IF EXISTS retail_mart CASCADE;
CREATE SCHEMA retail_mart;

CREATE TABLE retail_mart.dim_store (
    store_id UINTEGER PRIMARY KEY,
    store_name VARCHAR NOT NULL,
    city VARCHAR NOT NULL,
    region VARCHAR NOT NULL
);

CREATE TABLE retail_mart.dim_product (
    product_sk UBIGINT PRIMARY KEY,
    product_id UINTEGER NOT NULL,
    product_name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    brand VARCHAR NOT NULL,
    valid_from DATE NOT NULL,
    valid_to DATE,
    is_current BOOLEAN NOT NULL,
    UNIQUE (product_id, valid_from),
    CHECK (valid_to IS NULL OR valid_from < valid_to),
    CHECK (is_current = (valid_to IS NULL))
);

CREATE TABLE retail_mart.dim_date (
    date_id UINTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year USMALLINT NOT NULL,
    month UTINYINT NOT NULL,
    month_name VARCHAR NOT NULL,
    day_of_week UTINYINT NOT NULL
);

CREATE TABLE retail_mart.fact_sales (
    sale_id UBIGINT PRIMARY KEY,
    date_id UINTEGER NOT NULL REFERENCES retail_mart.dim_date(date_id),
    store_id UINTEGER NOT NULL REFERENCES retail_mart.dim_store(store_id),
    product_sk UBIGINT NOT NULL REFERENCES retail_mart.dim_product(product_sk),
    qty INTEGER NOT NULL CHECK (qty >= 0),
    amount DECIMAL(12, 2) NOT NULL CHECK (amount >= 0)
);
