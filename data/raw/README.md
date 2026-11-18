# Исходные данные

Первые четыре CSV — копии из Obsidian Vault, `Стенд/data/sample`. Кодировка UTF‑8. `product_category_changes.csv` — отдельно добавленное учебное событие для проверки SCD2.

| Файл | Строк | Поля |
|---|---:|---|
| `fact_sales.csv` | 15 | `sale_id` — ключ позиции, `date_id` — день, `store_id` — магазин, `product_id` — товар, `qty` — штук, `amount` — сумма позиции. |
| `dim_date.csv` | 8 | `date_id`, дата `full_date`, год `year`, месяц `month`, название месяца `month_name`, день недели ISO `day_of_week`. |
| `dim_store.csv` | 5 | `store_id`, название `store_name`, город `city`, регион `region`. |
| `dim_product.csv` | 8 | `product_id`, название `product_name`, исходная категория `category`, марка `brand`. |
| `product_category_changes.csv` | 1 | `product_id`, дата начала `effective_date`, новая `category`. С 01.02.2024 товар 101 «Молоко 1л» переводится из «Молочка» в «Молочные напитки». |
