# Exploratory Data Analysis Summary

## Scope

- **Customer records analyzed:** 21,000
- **Observed source records:** 7,043
- **Synthetic cohort scenario records:** 13,957
- **Observed churn rate:** 26.5%
- **Average tenure:** 32.4 months
- **Average monthly charge (MRR proxy):** $64.97

## Segment findings

1. **Month-to-month** customers have the highest observed churn rate (42.7%).
2. **Fiber optic** customers have the highest observed churn rate among internet-service groups (41.8%).
3. Customers in the **0–6 month onboarding window** show 53.2% observed churn, versus 14.0% for customers beyond 24 months.
4. **Electronic check** has the highest observed churn rate among payment methods (45.2%).
5. The estimated support-ticket measure is a service-configuration proxy, not an observed ticket count; use it for segmentation hypotheses only.

## Interpretation guardrails

- The source is a cross-sectional customer snapshot. It does not establish causality, true acquisition cohorts, or month-over-month revenue trends.
- The synthetic cohort rows preserve the observed population mix for scalable dashboard exploration, but they are not additional independent customers.
- `MonthlyCharges` and lifetime-value fields are revenue and value proxies, not audited financial statements.