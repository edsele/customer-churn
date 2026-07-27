-- Executive retention and revenue-risk snapshot
-- This concise output is suited to a dashboard KPI tile or a scheduled data
-- quality check.  It exposes original and augmented records separately.

SELECT
    record_source,
    customer_count,
    churned_customers,
    retained_customers,
    retention_rate_pct,
    mrr_snapshot,
    predicted_mrr_at_risk,
    scoring_coverage_pct
FROM v_retention_snapshot
ORDER BY record_source;
