SELECT product_sk, product_id, category, valid_from, valid_to, is_current
FROM retail_mart.dim_product
WHERE product_id = 101
ORDER BY valid_from;

SELECT d.full_date, f.sale_id, f.product_sk, p.category, f.amount
FROM retail_mart.fact_sales AS f
JOIN retail_mart.dim_date AS d ON d.date_id = f.date_id
JOIN retail_mart.dim_product AS p ON p.product_sk = f.product_sk
WHERE p.product_id = 101
ORDER BY d.full_date, f.sale_id;
