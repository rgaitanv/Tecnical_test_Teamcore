-- Vista resumen diaria
CREATE VIEW daily_transaction_summary AS
SELECT 
    DATE(ts) as transaction_date,
    status,
    COUNT(*) as transaction_count,
    SUM(amount) as total_amount,
    AVG(amount) as avg_amount,
    COUNT(DISTINCT user_id) as unique_users
FROM transactions
GROUP BY DATE(ts), status
ORDER BY transaction_date DESC, status;
