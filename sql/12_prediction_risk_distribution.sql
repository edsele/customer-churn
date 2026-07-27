-- Model score distribution and calibration snapshot
-- Comparing average predicted risk to observed churn is descriptive only.  Use
-- an out-of-time validation set for a formal calibration assessment.

SELECT
    record_source,
    risk_band,
    COUNT(*) AS customer_count,
    ROUND(100.0 * AVG(CASE WHEN churn_probability IS NOT NULL THEN 1.0 ELSE 0.0 END), 2)
        AS scored_customer_pct,
    ROUND(AVG(churn_probability), 4) AS avg_predicted_churn_probability,
    ROUND(100.0 * AVG(CASE WHEN observed_churn = 1 THEN 1.0 ELSE 0.0 END), 2)
        AS observed_churn_rate_pct,
    ROUND(SUM(COALESCE(revenue_at_risk, 0.0)), 2) AS predicted_mrr_at_risk,
    ROUND(AVG(decision_threshold), 4) AS avg_decision_threshold
FROM v_customer_analytics
GROUP BY record_source, risk_band
ORDER BY
    record_source,
    CASE risk_band
        WHEN 'High' THEN 1
        WHEN 'Medium' THEN 2
        WHEN 'Low' THEN 3
        WHEN 'Unclassified' THEN 4
        ELSE 5
    END;
