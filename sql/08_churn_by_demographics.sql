-- Churn by senior status and household composition
-- The Telco data provides a senior-citizen indicator, not an exact age.  This
-- report therefore uses age segment rather than asserting individual ages.

SELECT
    record_source,
    age_segment,
    partner,
    dependents,
    COUNT(*) AS customer_count,
    ROUND(100.0 * AVG(CASE WHEN observed_churn = 1 THEN 1.0 ELSE 0.0 END), 2)
        AS observed_churn_rate_pct,
    ROUND(AVG(tenure_months), 1) AS avg_tenure_months,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges,
    ROUND(AVG(churn_probability), 4) AS avg_predicted_churn_probability,
    ROUND(SUM(COALESCE(revenue_at_risk, 0.0)), 2) AS predicted_mrr_at_risk
FROM v_customer_analytics
GROUP BY record_source, age_segment, partner, dependents
ORDER BY observed_churn_rate_pct DESC, customer_count DESC;
