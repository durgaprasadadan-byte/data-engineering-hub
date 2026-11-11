"""Silver and Gold SQL for the e-commerce ELT.

Written in the common subset of Spark SQL and SQLite so the SAME statements run on
PySpark (Delta/Parquet), on the local SQLite fallback, and in a Databricks notebook.
Bronze tables are named bronze_<dataset> and hold raw values as strings.
"""
SILVER_SQL: list[tuple[str, str]] = [
    ("silver_customers", """
SELECT customer_id, name, email, country, signup_date FROM (
  SELECT TRIM(customer_id) AS customer_id, TRIM(name) AS name,
         COALESCE(LOWER(TRIM(email)), 'unknown') AS email, UPPER(TRIM(country)) AS country, signup_date,
         ROW_NUMBER() OVER (PARTITION BY TRIM(customer_id) ORDER BY signup_date) AS rn
  FROM bronze_customers) t
WHERE rn = 1"""),
    ("silver_products", """
SELECT product_id, product_name, category, unit_price FROM (
  SELECT TRIM(product_id) AS product_id, TRIM(product_name) AS product_name, TRIM(category) AS category,
         CAST(unit_price AS DOUBLE) AS unit_price,
         ROW_NUMBER() OVER (PARTITION BY TRIM(product_id) ORDER BY product_name) AS rn
  FROM bronze_products) t
WHERE rn = 1 AND unit_price IS NOT NULL AND unit_price >= 0.01"""),
    ("silver_orders", """
SELECT o.order_id, o.customer_id, o.product_id,
       CAST(CAST(o.quantity AS DOUBLE) AS INTEGER) AS quantity,
       o.order_date, SUBSTR(o.order_date, 1, 7) AS order_month, o.status, p.unit_price,
       CAST(CAST(o.quantity AS DOUBLE) AS INTEGER) * p.unit_price AS order_total
FROM (
  SELECT TRIM(order_id) AS order_id, TRIM(customer_id) AS customer_id, TRIM(product_id) AS product_id,
         quantity, TRIM(order_date) AS order_date, LOWER(TRIM(status)) AS status,
         ROW_NUMBER() OVER (PARTITION BY TRIM(order_id) ORDER BY order_date) AS rn
  FROM bronze_orders) o
JOIN silver_products p ON o.product_id = p.product_id
JOIN silver_customers c ON o.customer_id = c.customer_id
WHERE o.rn = 1 AND o.quantity IS NOT NULL AND CAST(CAST(o.quantity AS DOUBLE) AS INTEGER) >= 1"""),
    ("silver_payments", """
SELECT p.payment_id, p.order_id, p.amount, p.method, p.payment_date FROM (
  SELECT TRIM(payment_id) AS payment_id, TRIM(order_id) AS order_id, CAST(amount AS DOUBLE) AS amount,
         method, payment_date,
         ROW_NUMBER() OVER (PARTITION BY TRIM(payment_id) ORDER BY method) AS rn
  FROM bronze_payments) p
JOIN silver_orders o ON p.order_id = o.order_id
WHERE p.rn = 1 AND p.amount >= 0.01"""),
    ("silver_inventory", """
SELECT product_id, CAST(CAST(stock_qty AS DOUBLE) AS INTEGER) AS stock_qty, warehouse FROM (
  SELECT TRIM(product_id) AS product_id, stock_qty, warehouse,
         ROW_NUMBER() OVER (PARTITION BY TRIM(product_id) ORDER BY warehouse) AS rn
  FROM bronze_inventory) t
WHERE rn = 1 AND stock_qty IS NOT NULL AND CAST(stock_qty AS DOUBLE) >= 0"""),
]

GOLD_SQL: list[tuple[str, str]] = [
    ("gold_summary", """
SELECT COUNT(DISTINCT order_id) AS total_orders, ROUND(SUM(order_total), 2) AS total_revenue,
       ROUND(SUM(order_total) / COUNT(DISTINCT order_id), 2) AS avg_order_value
FROM silver_orders WHERE status <> 'cancelled'"""),
    ("gold_monthly_revenue", """
SELECT order_month, ROUND(SUM(order_total), 2) AS revenue, COUNT(*) AS orders
FROM silver_orders WHERE status <> 'cancelled' GROUP BY order_month ORDER BY order_month"""),
    ("gold_product_performance", """
SELECT p.product_id, p.product_name, p.category, SUM(o.quantity) AS units_sold,
       ROUND(SUM(o.order_total), 2) AS revenue
FROM silver_orders o JOIN silver_products p ON o.product_id = p.product_id
WHERE o.status <> 'cancelled'
GROUP BY p.product_id, p.product_name, p.category ORDER BY revenue DESC"""),
    ("gold_customer_segments", """
SELECT customer_id, total_spend, orders,
       CASE seg WHEN 1 THEN 'High' WHEN 2 THEN 'Medium' ELSE 'Low' END AS segment
FROM (
  SELECT customer_id, total_spend, orders, NTILE(3) OVER (ORDER BY total_spend DESC) AS seg FROM (
    SELECT customer_id, ROUND(SUM(order_total), 2) AS total_spend, COUNT(*) AS orders
    FROM silver_orders WHERE status <> 'cancelled' GROUP BY customer_id) a) b
ORDER BY total_spend DESC"""),
]

BRONZE_TABLES = ["customers", "products", "orders", "payments", "inventory"]
