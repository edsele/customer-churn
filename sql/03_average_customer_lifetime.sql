-- Customer tenure and value proxies by contract segment.
-- `tenure_months` is observed tenure at the snapshot. `total_charges` is a
-- cumulative-charge-to-date proxy, while the estimated field is a remaining
-- value proxy from feature engineering; neither is realized CLV.

SELECT
    record_source,
    contract_type,
    churn_status,
    COUNT(*) AS customer_count,
    ROUND(AVG(tenure_months), 1) AS avg_tenure_months,
    ROUND(AVG(total_charges), 2) AS avg_cumulative_charges_to_date_proxy,
    ROUND(AVG(lifetime_value_estimate), 2) AS avg_projected_remaining_value,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges,
    ROUND(AVG(avg_services_purchased), 2) AS avg_services_purchased
FROM v_customer_analytics
GROUP BY record_source, contract_type, churn_status
ORDER BY avg_tenure_months DESC, contract_type, churn_status;
