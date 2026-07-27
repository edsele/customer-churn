-- =============================================================================
-- Customer Churn & Behavioral Analytics | SQLite analytical data mart
-- =============================================================================
--
-- Run this script after loading `customers` and `customer_predictions`.
-- `customers` is the featured customer snapshot; `customer_predictions` stores
-- one current model score per customer.  The empty-table DDL below makes a
-- newly initialized database queryable before scores have been generated.
--
-- Prediction contract
-- -------------------
-- customerID, source_customer_id, model_name, model_version,
-- churn_probability, risk_band, is_high_risk, decision_threshold,
-- revenue_at_risk, score_source
--
-- `revenue_at_risk` represents probability-weighted monthly recurring revenue
-- at risk.  It is a model output, not revenue already lost to observed churn.

CREATE TABLE IF NOT EXISTS customer_predictions (
    customerID TEXT PRIMARY KEY,
    source_customer_id TEXT,
    model_name TEXT,
    model_version TEXT,
    churn_probability REAL CHECK (churn_probability BETWEEN 0.0 AND 1.0),
    risk_band TEXT CHECK (LOWER(risk_band) IN ('low', 'medium', 'high')),
    is_high_risk INTEGER CHECK (is_high_risk IN (0, 1)),
    decision_threshold REAL CHECK (decision_threshold BETWEEN 0.0 AND 1.0),
    revenue_at_risk REAL CHECK (revenue_at_risk >= 0.0),
    score_source TEXT
);

-- These indexes support the customer-to-score join and common report filters.
CREATE UNIQUE INDEX IF NOT EXISTS ux_customers_customer_id
    ON customers (customerID);
CREATE INDEX IF NOT EXISTS idx_customers_contract_churn
    ON customers (Contract, Churn);
CREATE INDEX IF NOT EXISTS idx_customer_predictions_customer_id
    ON customer_predictions (customerID);
CREATE INDEX IF NOT EXISTS idx_customer_predictions_risk_band
    ON customer_predictions (risk_band);

-- Drop dependent views before rebuilding the base view.
DROP VIEW IF EXISTS v_high_risk_customers;
DROP VIEW IF EXISTS v_retention_snapshot;
DROP VIEW IF EXISTS v_customer_segments;
DROP VIEW IF EXISTS v_customer_analytics;

-- Canonical reporting view.  All analysis scripts select from this view so
-- score definitions and customer field aliases stay consistent across reports.
CREATE VIEW v_customer_analytics AS
SELECT
    c.customerID AS customer_id,
    COALESCE(c.record_source, 'unknown') AS record_source,
    c.gender AS gender,
    CASE
        WHEN c.SeniorCitizen = 1 THEN 'Senior (65+)'
        WHEN c.SeniorCitizen = 0 THEN 'Non-senior'
        ELSE 'Unknown'
    END AS age_segment,
    c.Partner AS partner,
    c.Dependents AS dependents,
    c.Contract AS contract_type,
    c.InternetService AS internet_service,
    c.PaymentMethod AS payment_method,
    c.PaperlessBilling AS paperless_billing,
    CAST(c.tenure AS INTEGER) AS tenure_months,
    c.tenure_bucket AS tenure_bucket,
    CAST(c.MonthlyCharges AS REAL) AS monthly_charges,
    CAST(c.TotalCharges AS REAL) AS total_charges,
    CAST(COALESCE(c.support_ticket_proxy, 0) AS INTEGER) AS support_ticket_proxy,
    CAST(COALESCE(c.support_intensity, 0.0) AS REAL) AS support_intensity,
    CAST(COALESCE(c.avg_services_purchased, 0) AS INTEGER) AS avg_services_purchased,
    CAST(COALESCE(c.contract_risk_score, 0) AS INTEGER) AS contract_risk_score,
    CAST(COALESCE(c.payment_risk_flag, 0) AS INTEGER) AS payment_risk_flag,
    CAST(COALESCE(c.customer_engagement_score, 0.0) AS REAL) AS customer_engagement_score,
    CAST(COALESCE(c.lifetime_value_estimate, 0.0) AS REAL) AS lifetime_value_estimate,
    CAST(c.Churn AS INTEGER) AS observed_churn,
    CASE
        WHEN c.Churn = 1 THEN 'Churned'
        WHEN c.Churn = 0 THEN 'Retained'
        ELSE 'Unknown'
    END AS churn_status,
    p.source_customer_id AS source_customer_id,
    p.model_name AS model_name,
    p.model_version AS model_version,
    CASE
        WHEN p.churn_probability BETWEEN 0.0 AND 1.0
            THEN ROUND(p.churn_probability, 4)
        ELSE NULL
    END AS churn_probability,
    CASE
        WHEN LOWER(TRIM(p.risk_band)) = 'high' THEN 'High'
        WHEN LOWER(TRIM(p.risk_band)) = 'medium' THEN 'Medium'
        WHEN LOWER(TRIM(p.risk_band)) = 'low' THEN 'Low'
        WHEN p.churn_probability IS NULL THEN 'Unscored'
        ELSE 'Unclassified'
    END AS risk_band,
    CASE
        WHEN p.is_high_risk IN (0, 1) THEN p.is_high_risk
        WHEN p.churn_probability IS NULL THEN NULL
        WHEN p.churn_probability >= COALESCE(p.decision_threshold, 0.50) THEN 1
        ELSE 0
    END AS is_high_risk,
    CASE
        WHEN p.decision_threshold BETWEEN 0.0 AND 1.0
            THEN ROUND(p.decision_threshold, 4)
        ELSE NULL
    END AS decision_threshold,
    CASE
        WHEN p.revenue_at_risk >= 0.0 THEN ROUND(p.revenue_at_risk, 2)
        WHEN p.churn_probability BETWEEN 0.0 AND 1.0
            THEN ROUND(COALESCE(c.MonthlyCharges, 0.0) * p.churn_probability, 2)
        ELSE NULL
    END AS revenue_at_risk,
    p.score_source AS score_source
FROM customers AS c
LEFT JOIN customer_predictions AS p
    ON p.customerID = c.customerID;

-- Reusable lifecycle, revenue, and intervention segments for reporting.
CREATE VIEW v_customer_segments AS
SELECT
    a.*,
    CASE
        WHEN a.tenure_months <= 6 THEN '0-6 months: onboarding'
        WHEN a.tenure_months <= 24 THEN '7-24 months: growth'
        WHEN a.tenure_months <= 48 THEN '25-48 months: mature'
        ELSE '49+ months: loyal'
    END AS tenure_segment,
    CASE
        WHEN a.monthly_charges < 35.0 THEN 'Budget: under $35'
        WHEN a.monthly_charges < 70.0 THEN 'Standard: $35-$69.99'
        WHEN a.monthly_charges < 100.0 THEN 'Premium: $70-$99.99'
        ELSE 'Premium plus: $100+'
    END AS monthly_revenue_tier,
    CASE
        WHEN a.churn_probability IS NULL THEN 'No model score'
        WHEN a.is_high_risk = 1 AND a.monthly_charges >= 70.0
            THEN 'Priority retention outreach'
        WHEN a.is_high_risk = 1 THEN 'Standard retention outreach'
        WHEN a.risk_band = 'Medium' THEN 'Monitor'
        ELSE 'No immediate action'
    END AS retention_priority
FROM v_customer_analytics AS a;

-- Customer-level worklist for proactive retention.  This view intentionally
-- relies on model outputs rather than observed churn, preventing label leakage.
CREATE VIEW v_high_risk_customers AS
SELECT
    customer_id,
    source_customer_id,
    record_source,
    contract_type,
    internet_service,
    payment_method,
    tenure_months,
    tenure_segment,
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
FROM v_customer_segments
WHERE is_high_risk = 1
   OR risk_band = 'High';

-- Cross-sectional retention snapshot.  This data set is a point-in-time
-- extract, so these are retained shares by population rather than true cohorts.
CREATE VIEW v_retention_snapshot AS
SELECT
    record_source,
    COUNT(*) AS customer_count,
    SUM(CASE WHEN observed_churn = 1 THEN 1 ELSE 0 END) AS churned_customers,
    SUM(CASE WHEN observed_churn = 0 THEN 1 ELSE 0 END) AS retained_customers,
    ROUND(100.0 * AVG(CASE WHEN observed_churn = 0 THEN 1.0 ELSE 0.0 END), 2)
        AS retention_rate_pct,
    ROUND(SUM(monthly_charges), 2) AS mrr_snapshot,
    ROUND(SUM(COALESCE(revenue_at_risk, 0.0)), 2) AS predicted_mrr_at_risk,
    ROUND(100.0 * AVG(CASE WHEN churn_probability IS NOT NULL THEN 1.0 ELSE 0.0 END), 2)
        AS scoring_coverage_pct
FROM v_customer_analytics
GROUP BY record_source;
