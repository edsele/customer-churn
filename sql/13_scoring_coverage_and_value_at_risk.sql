-- Scoring coverage and expected revenue exposure
-- Operational monitoring query: a drop in coverage indicates customers reached
-- the dashboard without a fresh model score or a valid prediction join.

SELECT
    record_source,
    COUNT(*) AS customer_count,
    SUM(CASE WHEN churn_probability IS NOT NULL THEN 1 ELSE 0 END) AS scored_customers,
    ROUND(100.0 * AVG(CASE WHEN churn_probability IS NOT NULL THEN 1.0 ELSE 0.0 END), 2)
        AS scoring_coverage_pct,
    SUM(CASE WHEN is_high_risk = 1 THEN 1 ELSE 0 END) AS high_risk_customers,
    ROUND(100.0 * AVG(CASE WHEN is_high_risk = 1 THEN 1.0 ELSE 0.0 END), 2)
        AS high_risk_customer_pct,
    ROUND(SUM(monthly_charges), 2) AS mrr_snapshot,
    ROUND(SUM(COALESCE(revenue_at_risk, 0.0)), 2) AS predicted_mrr_at_risk,
    ROUND(
        100.0 * SUM(COALESCE(revenue_at_risk, 0.0))
        / NULLIF(SUM(monthly_charges), 0.0),
        2
    ) AS mrr_at_risk_pct
FROM v_customer_analytics
GROUP BY record_source
ORDER BY record_source;
