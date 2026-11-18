SELECT COALESCE(SUM(f.amount), CAST(0 AS DECIMAL(38, 2))) AS turnover
FROM retail_mart.fact_sales AS f
JOIN retail_mart.dim_date AS d ON d.date_id = f.date_id
WHERE d.full_date >= CAST('2024-01-01' AS DATE)
  AND d.full_date < CAST('2024-04-01' AS DATE)
  [[AND f.store_id IN (SELECT store_id FROM retail_mart.dim_store WHERE {{region}})]]
