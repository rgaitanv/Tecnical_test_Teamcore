-- Detección de anomalías: comparar conteos diarios y alertar incrementos significativos.
CREATE or replace VIEW daily_anomaly_detection AS
WITH daily_counts AS (
    SELECT 
        DATE(ts) as transaction_date,
        status,
        COUNT(*) as daily_count
    FROM transactions
    GROUP BY DATE(ts), status
),
trend_analysis AS (
    SELECT 
        transaction_date,
        status,
        daily_count,
        LAG(daily_count, 1) OVER (PARTITION BY status ORDER BY transaction_date) as prev_day_count,
        LAG(daily_count, 7) OVER (PARTITION BY status ORDER BY transaction_date) as week_ago_count,
        AVG(daily_count) OVER (
            PARTITION BY status 
            ORDER BY transaction_date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) as avg_7_days
    FROM daily_counts
)
SELECT 
    transaction_date,
    status,
    daily_count,
    prev_day_count,
    week_ago_count,
    ROUND(avg_7_days, 2) as avg_7_days,
    CASE 
        WHEN prev_day_count > 0 THEN 
            ROUND(((daily_count - prev_day_count) * 100.0 / prev_day_count), 2)
        ELSE NULL 
    END as pct_change_vs_yesterday,
    CASE 
        WHEN avg_7_days > 0 THEN 
            ROUND(((daily_count - avg_7_days) * 100.0 / avg_7_days), 2)
        ELSE NULL 
    END as pct_deviation_from_avg,
    CASE 
        WHEN daily_count > avg_7_days * 1.5 THEN 'HIGH_ANOMALY'
        WHEN daily_count > avg_7_days * 1.1 THEN 'MODERATE_ANOMALY'
        WHEN daily_count < avg_7_days * 0.8 THEN 'LOW_ANOMALY'
        ELSE 'NORMAL'
    END as anomaly_flag
FROM trend_analysis
ORDER BY transaction_date DESC, status;
