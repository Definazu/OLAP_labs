-- Ограничение по ведущему ключу и явный фильтр по выражению партиции.
EXPLAIN indexes = 1
SELECT sum(amount) FROM retail_mart.fact_sales
WHERE date_id BETWEEN 20240101 AND 20240131 AND intDiv(date_id, 100) = 202401;

-- Только магазин: без ограничения ведущей даты/месяца.
EXPLAIN indexes = 1
SELECT sum(amount) FROM retail_mart.fact_sales WHERE store_id = 1;
