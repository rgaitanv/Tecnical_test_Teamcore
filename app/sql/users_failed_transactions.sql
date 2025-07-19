-- Query para detectar usuarios con >3 transacciones fallidas en los últimos 7 días.
create or replace VIEW users_failed_transactions as
WITH latest_date AS (
    SELECT MAX(DATE(ts)) as max_date FROM transactions
)
SELECT 
    user_id,
    COUNT(*) as failed_transactions
FROM transactions, latest_date
WHERE status = 'failed'
    AND ts >= latest_date.max_date - INTERVAL '7 days'
GROUP BY user_id
HAVING COUNT(*) > 3
ORDER BY failed_transactions DESC;