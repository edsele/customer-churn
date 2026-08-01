-- Revenue and risk exposure by contract type.
-- MRR is a point-in-time monthly recurring-revenue proxy. `total_charges` is
-- a cumulative-charge-to-date proxy from the cross-sectional source, not
-- realized lifetime revenue or an audited finance measure.

SELECT
    record_source,
    contract_type,
    COUNT(*) AS customer_count,
    ROUND(SUM(monthly_charges), 2) AS mrr_snapshot,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges,
    ROUND(SUM(total_charges), 2) AS cumulative_charges_to_date_proxy,
    ROUND(SUM(CASE WHEN observed_churn = 1 THEN monthly_charges ELSE 0.0 END), 2)
        AS observed_churned_mrr,
    ROUND(SUM(COALESCE(revenue_at_risk, 0.0)), 2) AS predicted_mrr_at_risk,
    ROUND(100.0 * AVG(CASE WHEN observed_churn = 1 THEN 1.0 ELSE 0.0 END), 2)
        AS churn_rate_pct
FROM v_customer_analytics
GROUP BY record_source, contract_type
ORDER BY mrr_snapshot DESC, contract_type;
