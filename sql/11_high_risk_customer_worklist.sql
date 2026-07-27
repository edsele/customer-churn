-- High-risk customer worklist for retention operations
-- This customer-level output can be exported to a CRM campaign after applying
-- the business's contact-consent and offer-eligibility rules outside SQLite.

SELECT
    customer_id,
    source_customer_id,
    record_source,
    contract_type,
    internet_service,
    payment_method,
    tenure_months,
    monthly_charges,
    support_ticket_proxy,
    customer_engagement_score,
    churn_probability,
    risk_band,
    decision_threshold,
    revenue_at_risk,
    retention_priority,
    model_name,
    model_version,
    score_source
FROM v_high_risk_customers
ORDER BY revenue_at_risk DESC, churn_probability DESC, customer_id
LIMIT 100;
