SELECT toStartOfMonth(d.full_date) AS sale_month, SUM(a.turnover) AS turnover
FROM retail_mart.agg_daily_store AS a
JOIN retail_mart.dim_date AS d ON d.date_id = a.date_id
WHERE d.full_date >= CAST('2024-01-01' AS DATE)
  AND d.full_date < CAST('2024-04-01' AS DATE)
  [[AND a.store_id IN (SELECT store_id FROM retail_mart.dim_store WHERE {{region}})]]
GROUP BY sale_month
ORDER BY sale_month
