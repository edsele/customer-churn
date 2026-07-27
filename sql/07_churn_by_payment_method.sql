-- Churn and model-risk analysis by payment method and billing preference
-- Payment behavior is useful for retention design, for example by prioritizing
-- electronic-check customers for auto-pay migration campaigns.

SELECT
    record_source,
    payment_method,
    paperless_billing,
    COUNT(*) AS customer_count,
    ROUND(100.0 * AVG(CASE WHEN observed_churn = 1 THEN 1.0 ELSE 0.0 END), 2)
        AS observed_churn_rate_pct,
    ROUND(AVG(churn_probability), 4) AS avg_predicted_churn_probability,
    ROUND(AVG(support_ticket_proxy), 2) AS avg_support_ticket_proxy,
    ROUND(SUM(monthly_charges), 2) AS mrr_snapshot,
    ROUND(SUM(COALESCE(revenue_at_risk, 0.0)), 2) AS predicted_mrr_at_risk
FROM v_customer_analytics
GROUP BY record_source, payment_method, paperless_billing
ORDER BY observed_churn_rate_pct DESC, customer_count DESC;
