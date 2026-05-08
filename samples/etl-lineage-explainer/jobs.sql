-- Sample ETL jobs demonstrating common patterns

CREATE TABLE analytics.daily_orders AS
SELECT
  o.order_id,
  o.customer_id,
  o.order_date,
  p.product_id,
  p.category
FROM raw.orders o
JOIN raw.products p
  ON o.product_id = p.product_id
WHERE o.order_date >= DATE '2026-01-01';

INSERT INTO analytics.customer_order_counts
SELECT
  customer_id,
  COUNT(*) AS order_count
FROM raw.orders
GROUP BY customer_id;

CREATE VIEW analytics.active_customers AS
SELECT c.customer_id
FROM raw.customers c
JOIN analytics.customer_order_counts coc
  ON c.customer_id = coc.customer_id
WHERE coc.order_count >= 2;
