-- Model-driven high-risk customer groups
-- Use this aggregation to target retention programs.  Only scored customers
-- are included, preventing unscored records from diluting model-risk metrics.

SELECT
    record_source,
    risk_band,
    contract_type,
    tenure_segment,
    COUNT(*) AS scored_customers,
    ROUND(AVG(churn_probability), 4) AS avg_churn_probability,
    ROUND(SUM(COALESCE(revenue_at_risk, 0.0)), 2) AS total_revenue_at_risk,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges,
    ROUND(100.0 * AVG(CASE WHEN observed_churn = 1 THEN 1.0 ELSE 0.0 END), 2)
        AS observed_churn_rate_pct
FROM v_customer_segments
WHERE churn_probability IS NOT NULL
GROUP BY record_source, risk_band, contract_type, tenure_segment
HAVING COUNT(*) >= 25
ORDER BY total_revenue_at_risk DESC, avg_churn_probability DESC;
