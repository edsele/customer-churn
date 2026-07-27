-- Churn by support-ticket proxy intensity
-- `support_ticket_proxy` is an engineered behavioral proxy, not a feed of
-- observed support tickets.  Treat this analysis as directional unless an
-- operational ticketing-system source is integrated.

WITH ticket_segments AS (
    SELECT
        *,
        CASE
            WHEN support_ticket_proxy = 0 THEN '0 proxy contacts'
            WHEN support_ticket_proxy <= 2 THEN '1-2 proxy contacts'
            WHEN support_ticket_proxy <= 5 THEN '3-5 proxy contacts'
            ELSE '6+ proxy contacts'
        END AS support_proxy_segment
    FROM v_customer_analytics
)
SELECT
    record_source,
    support_proxy_segment,
    COUNT(*) AS customer_count,
    ROUND(100.0 * AVG(CASE WHEN observed_churn = 1 THEN 1.0 ELSE 0.0 END), 2)
        AS observed_churn_rate_pct,
    ROUND(AVG(churn_probability), 4) AS avg_predicted_churn_probability,
    ROUND(AVG(customer_engagement_score), 2) AS avg_engagement_score,
    ROUND(AVG(monthly_charges), 2) AS avg_monthly_charges,
    ROUND(SUM(COALESCE(revenue_at_risk, 0.0)), 2) AS predicted_mrr_at_risk
FROM ticket_segments
GROUP BY record_source, support_proxy_segment
ORDER BY record_source, MIN(support_ticket_proxy);
