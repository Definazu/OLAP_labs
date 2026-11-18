INSERT INTO retail_mart.dim_store SELECT * FROM raw_store;
INSERT INTO retail_mart.dim_date SELECT * FROM raw_date;

INSERT INTO retail_mart.dim_product
WITH category_history AS (
    SELECT product_id, category, (SELECT MIN(full_date) FROM raw_date) AS valid_from
    FROM raw_product
    UNION ALL
    SELECT product_id, category, effective_date FROM raw_changes
), versions AS (
    SELECT *, LEAD(valid_from) OVER (PARTITION BY product_id ORDER BY valid_from) AS valid_to
    FROM category_history
)
SELECT CAST(v.product_id AS UBIGINT) * 100000000 + CAST(strftime(v.valid_from, '%Y%m%d') AS UBIGINT),
       v.product_id, p.product_name, v.category, p.brand, v.valid_from, v.valid_to, v.valid_to IS NULL
FROM versions AS v
JOIN raw_product AS p ON p.product_id = v.product_id;

-- Левый JOIN позволяет ограничению NOT NULL выявить факт без версии.
-- PRIMARY KEY(sale_id) выявит противоречивую привязку одного факта к нескольким версиям.
INSERT INTO retail_mart.fact_sales
SELECT f.sale_id, f.date_id, f.store_id, p.product_sk, f.qty, CAST(f.amount AS DECIMAL(12, 2))
FROM raw_sales AS f
JOIN retail_mart.dim_date AS d ON d.date_id = f.date_id
LEFT JOIN retail_mart.dim_product AS p ON p.product_id = f.product_id
    AND d.full_date >= p.valid_from AND (d.full_date < p.valid_to OR p.valid_to IS NULL);
