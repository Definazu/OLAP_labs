SELECT p.category, SUM(f.amount) AS turnover
FROM retail_mart.fact_sales AS f
JOIN retail_mart.dim_product AS p ON p.product_sk = f.product_sk
WHERE f.date_id >= 20240101 AND f.date_id < 20240401
  [[AND f.store_id IN (SELECT store_id FROM retail_mart.dim_store WHERE {{region}})]]
GROUP BY p.category
ORDER BY turnover DESC, p.category
