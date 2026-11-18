SELECT 'empty snapshot' AS validation, COUNT(*) AS violations
FROM (SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM raw_sales))
UNION ALL
SELECT 'missing keys, attributes or measures',
    (SELECT COUNT(*) FROM raw_sales WHERE sale_id IS NULL OR date_id IS NULL
        OR store_id IS NULL OR product_id IS NULL OR qty IS NULL OR amount IS NULL)
  + (SELECT COUNT(*) FROM raw_store WHERE store_id IS NULL OR trim(coalesce(store_name, '')) = ''
        OR trim(coalesce(city, '')) = '' OR trim(coalesce(region, '')) = '')
  + (SELECT COUNT(*) FROM raw_product WHERE product_id IS NULL OR trim(coalesce(product_name, '')) = ''
        OR trim(coalesce(category, '')) = '' OR trim(coalesce(brand, '')) = '')
  + (SELECT COUNT(*) FROM raw_date WHERE date_id IS NULL OR full_date IS NULL OR year IS NULL
        OR month IS NULL OR trim(coalesce(month_name, '')) = '' OR day_of_week IS NULL)
  + (SELECT COUNT(*) FROM raw_changes WHERE product_id IS NULL OR effective_date IS NULL
        OR trim(coalesce(category, '')) = '')
UNION ALL
SELECT 'invalid quantity, amount, keys or date',
    (SELECT COUNT(*) FROM raw_sales WHERE qty < 0 OR sale_id = 0
        OR NOT regexp_full_match(amount, '[0-9]{1,10}(\.[0-9]{1,2})?'))
  + (SELECT COUNT(*) FROM raw_store WHERE store_id = 0)
  + (SELECT COUNT(*) FROM raw_product WHERE product_id = 0)
  + (SELECT COUNT(*) FROM raw_date WHERE full_date < DATE '2000-01-01' OR full_date > DATE '2100-12-31'
        OR date_id != CAST(strftime(full_date, '%Y%m%d') AS UINTEGER)
        OR year != year(full_date) OR month != month(full_date) OR day_of_week != isodow(full_date))
  + (SELECT COUNT(*) FROM raw_changes WHERE effective_date <= (SELECT MIN(full_date) FROM raw_date)
        OR effective_date > DATE '2100-12-31')
UNION ALL
SELECT 'duplicate business keys',
    (SELECT COUNT(*) FROM (SELECT sale_id FROM raw_sales GROUP BY sale_id HAVING COUNT(*) > 1))
  + (SELECT COUNT(*) FROM (SELECT store_id FROM raw_store GROUP BY store_id HAVING COUNT(*) > 1))
  + (SELECT COUNT(*) FROM (SELECT product_id FROM raw_product GROUP BY product_id HAVING COUNT(*) > 1))
  + (SELECT COUNT(*) FROM (SELECT date_id FROM raw_date GROUP BY date_id HAVING COUNT(*) > 1))
  + (SELECT COUNT(*) FROM (SELECT product_id, effective_date FROM raw_changes
        GROUP BY product_id, effective_date HAVING COUNT(*) > 1))
UNION ALL
SELECT 'missing references',
    (SELECT COUNT(*) FROM raw_sales AS f WHERE NOT EXISTS (SELECT 1 FROM raw_store AS s WHERE s.store_id = f.store_id)
        OR NOT EXISTS (SELECT 1 FROM raw_date AS d WHERE d.date_id = f.date_id)
        OR NOT EXISTS (SELECT 1 FROM raw_product AS p WHERE p.product_id = f.product_id))
  + (SELECT COUNT(*) FROM raw_changes AS c WHERE NOT EXISTS
        (SELECT 1 FROM raw_product AS p WHERE p.product_id = c.product_id));
