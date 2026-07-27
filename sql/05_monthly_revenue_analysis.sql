-- Monthly recurring revenue (MRR) snapshot by revenue tier
-- The data is cross-sectional.  The query reports current MRR and expected MRR
-- at risk, rather than fabricating month-over-month revenue movement.

SELECT
    record_source,
    monthly_revenue_tier,
    COUNT(*) AS customer_count,
    ROUND(SUM(monthly_charges), 2) AS mrr_snapshot,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges,
    ROUND(SUM(CASE WHEN observed_churn = 1 THEN monthly_charges ELSE 0.0 END), 2)
        AS observed_churned_mrr,
    ROUND(SUM(COALESCE(revenue_at_risk, 0.0)), 2) AS predicted_mrr_at_risk,
    ROUND(100.0 * AVG(CASE WHEN observed_churn = 1 THEN 1.0 ELSE 0.0 END), 2)
        AS observed_churn_rate_pct
FROM v_customer_segments
GROUP BY record_source, monthly_revenue_tier
ORDER BY mrr_snapshot DESC;
