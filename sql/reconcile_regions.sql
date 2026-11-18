SELECT CASE WHEN GROUPING(s.region) = 1 THEN 'Все регионы' ELSE s.region END AS scope,
       COUNT(*) AS positions,
       SUM(f.amount) AS turnover
FROM retail_mart.fact_sales AS f
JOIN retail_mart.dim_date AS d ON d.date_id = f.date_id
JOIN retail_mart.dim_store AS s ON s.store_id = f.store_id
WHERE d.full_date >= CAST('2024-01-01' AS DATE)
  AND d.full_date < CAST('2024-04-01' AS DATE)
GROUP BY GROUPING SETS ((s.region), ())
ORDER BY GROUPING(s.region) DESC, scope;
