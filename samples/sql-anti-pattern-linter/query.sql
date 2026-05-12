-- Sample query with multiple intentional anti-patterns
SELECT *
FROM users u, orders o
WHERE LOWER(u.email) = 'alice@example.com'
  AND o.user_id = u.id
  AND u.status = 'active' OR u.status = 'trial'
  AND u.name LIKE '%son'
  AND u.id NOT IN (SELECT user_id FROM banned_users);
