-- Projected customer value by service segment
-- `lifetime_value_estimate` is the modelled remaining-value feature.  It is
-- reported alongside realized charges to make that interpretation transparent.

SELECT
    record_source,
    contract_type,
    internet_service,
    tenure_segment,
    COUNT(*) AS customer_count,
    ROUND(AVG(lifetime_value_estimate), 2) AS avg_projected_customer_value,
    ROUND(SUM(lifetime_value_estimate), 2) AS total_projected_customer_value,
    ROUND(AVG(total_charges), 2) AS avg_realized_lifetime_revenue,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges,
    ROUND(100.0 * AVG(CASE WHEN observed_churn = 1 THEN 1.0 ELSE 0.0 END), 2)
        AS observed_churn_rate_pct
FROM v_customer_segments
GROUP BY record_source, contract_type, internet_service, tenure_segment
HAVING COUNT(*) >= 25
ORDER BY avg_projected_customer_value DESC, customer_count DESC;
