SELECT concat(s.store_name, ' · ', s.city) AS store, SUM(f.amount) AS turnover
FROM retail_mart.fact_sales AS f
JOIN retail_mart.dim_store AS s ON s.store_id = f.store_id
WHERE f.date_id >= 20240101 AND f.date_id < 20240401
  [[AND f.store_id IN (SELECT store_id FROM retail_mart.dim_store WHERE {{region}})]]
GROUP BY s.store_id, s.store_name, s.city
ORDER BY turnover DESC, s.store_id
LIMIT 3
