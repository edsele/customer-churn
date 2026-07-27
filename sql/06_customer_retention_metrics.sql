-- Cross-sectional retention snapshot by lifecycle segment
-- This is not a longitudinal cohort-retention calculation because the source
-- dataset contains no event date or periodic account-status history.

SELECT
    record_source,
    tenure_segment,
    COUNT(*) AS customer_count,
    SUM(CASE WHEN observed_churn = 0 THEN 1 ELSE 0 END) AS retained_customers,
    SUM(CASE WHEN observed_churn = 1 THEN 1 ELSE 0 END) AS churned_customers,
    ROUND(100.0 * AVG(CASE WHEN observed_churn = 0 THEN 1.0 ELSE 0.0 END), 2)
        AS retention_rate_pct,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges,
    ROUND(SUM(COALESCE(revenue_at_risk, 0.0)), 2) AS predicted_mrr_at_risk
FROM v_customer_segments
GROUP BY record_source, tenure_segment
ORDER BY record_source, MIN(tenure_months);
