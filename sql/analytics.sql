-- 1. Как менялся оборот магазинов по месяцам в I квартале 2024 года?
SELECT d.year AS sale_year, d.month AS sale_month, s.store_id, s.store_name,
       SUM(f.amount) AS turnover
FROM retail_mart.fact_sales AS f
JOIN retail_mart.dim_date AS d ON d.date_id = f.date_id
JOIN retail_mart.dim_store AS s ON s.store_id = f.store_id
WHERE d.full_date >= CAST('2024-01-01' AS DATE)
  AND d.full_date < CAST('2024-04-01' AS DATE)
GROUP BY d.year, d.month, s.store_id, s.store_name
ORDER BY sale_year, sale_month, s.store_id;

-- 2. Какие категории дали наибольший оборот в каждом регионе квартала?
WITH by_category AS (
    SELECT s.region, p.category, SUM(f.amount) AS turnover
    FROM retail_mart.fact_sales AS f
    JOIN retail_mart.dim_store AS s ON s.store_id = f.store_id
    JOIN retail_mart.dim_product AS p ON p.product_sk = f.product_sk
    WHERE f.date_id >= 20240101 AND f.date_id < 20240401
    GROUP BY s.region, p.category
)
SELECT region, category, turnover,
       DENSE_RANK() OVER (PARTITION BY region ORDER BY turnover DESC) AS category_rank
FROM by_category
ORDER BY region, category_rank, category;

-- 3. Какие три магазина лидировали по обороту в I квартале 2024 года?
SELECT s.store_id, s.store_name, s.city, SUM(f.amount) AS turnover
FROM retail_mart.fact_sales AS f
JOIN retail_mart.dim_store AS s ON s.store_id = f.store_id
WHERE f.date_id >= 20240101 AND f.date_id < 20240401
GROUP BY s.store_id, s.store_name, s.city
ORDER BY turnover DESC, s.store_id
LIMIT 3;

-- 4. Slice: оборот Запада за январь по наблюдаемым дням.
SELECT d.full_date AS sale_day, SUM(f.amount) AS turnover
FROM retail_mart.fact_sales AS f
JOIN retail_mart.dim_date AS d ON d.date_id = f.date_id
JOIN retail_mart.dim_store AS s ON s.store_id = f.store_id
WHERE d.full_date >= CAST('2024-01-01' AS DATE)
  AND d.full_date < CAST('2024-02-01' AS DATE)
  AND s.region = 'Запад'
GROUP BY d.full_date
ORDER BY sale_day;

-- 5. Roll-up: оборот по месяцам и итоги по году на имеющихся датах.
SELECT d.year AS sale_year,
       CASE WHEN GROUPING(d.month) = 1 THEN 0 ELSE d.month END AS sale_month,
       SUM(f.amount) AS turnover
FROM retail_mart.fact_sales AS f
JOIN retail_mart.dim_date AS d ON d.date_id = f.date_id
GROUP BY GROUPING SETS ((d.year, d.month), (d.year))
ORDER BY sale_year, sale_month;
