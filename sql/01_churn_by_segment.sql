-- Churn by customer segment
-- Business question: Which contract, internet, and lifecycle combinations have
-- the greatest observed churn?  Results retain the source flag so augmented
-- records can be distinguished from the original public-data population.

SELECT
    record_source,
    contract_type,
    internet_service,
    tenure_segment,
    COUNT(*) AS customer_count,
    SUM(CASE WHEN observed_churn = 1 THEN 1 ELSE 0 END) AS churned_customers,
    ROUND(100.0 * AVG(CASE WHEN observed_churn = 1 THEN 1.0 ELSE 0.0 END), 2)
        AS churn_rate_pct,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges,
    ROUND(AVG(churn_probability), 4) AS avg_predicted_churn_probability
FROM v_customer_segments
GROUP BY
    record_source,
    contract_type,
    internet_service,
    tenure_segment
HAVING COUNT(*) >= 25
ORDER BY churn_rate_pct DESC, customer_count DESC;
