# Exploratory Data Analysis Summary

## Scope

- **Observed source customers analyzed:** 7,043
- **Synthetic scenario records excluded from findings:** 13,957
- **Observed churn rate:** 26.5%
- **Average tenure:** 32.4 months
- **Average monthly charge (MRR proxy):** $64.76

## Segment findings

1. **Month-to-month** customers have the highest observed churn rate (42.7%).
2. **Fiber optic** customers have the highest observed churn rate among internet-service groups (41.9%).
3. Customers in the **0-6 month onboarding window** show 52.9% observed churn, versus 14.0% for customers beyond 24 months.
4. **Electronic check** has the highest observed churn rate among payment methods (45.3%).
5. The estimated support-contact measure is a service-configuration proxy, not an observed ticket count; use it for segmentation hypotheses only.

## Interpretation guardrails

- The source is a cross-sectional customer snapshot. It does not establish causality, true acquisition cohorts, or month-over-month revenue trends.
- Scenario descendants are retained for a clearly labeled dashboard prototype, not used as independent evidence for the findings above.
- `MonthlyCharges` and remaining-value fields are revenue and value proxies, not audited financial statements.