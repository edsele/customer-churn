# Feature Engineering Documentation

All features are calculated from attributes available in the customer snapshot.
The churn label is never used to create a feature.

| Feature | Description | Intended use |
|---|---|---|
| `tenure_bucket` | Lifecycle stage derived from tenure in months. | Model and dashboard |
| `revenue_per_month` | Realized charges divided by tenure; uses MonthlyCharges for new customers. | Model and dashboard |
| `service_count` | Count of active connectivity, protection, support, and streaming services. | Model and dashboard |
| `avg_services_purchased` | Compatibility label for the per-customer active service count. | Dashboard only |
| `contract_risk_score` | Business-rule score for contract flexibility; 3 is month-to-month, 1 is two-year. | Dashboard only; raw Contract is modelled categorically |
| `customer_engagement_score` | Explainable composite of adopted services, security add-ons, tenure, and contract depth. | Model and dashboard |
| `monthly_charge_ratio` | Monthly charge relative to the scenario median; descriptive only. | Dashboard only |
| `lifetime_value_estimate` | Remaining-revenue proxy: MonthlyCharges multiplied by months remaining to a 72-month horizon. | Dashboard only |
| `payment_risk_flag` | Electronic-check indicator used as a descriptive operational signal. | Model and dashboard |
| `senior_household_flag` | Senior customer without partner or dependents. | Model and dashboard |
| `internet_fiber_flag` | Fiber-optic service indicator for dashboard segmentation. | Dashboard only; raw InternetService is modelled categorically |
| `support_ticket_proxy` | Estimated support need from service setup and tenure, not an observed ticket count. | Dashboard only |
| `support_intensity` | Estimated support need normalized by tenure, with new customers protected from division by zero. | Dashboard only |

## Modeling boundary

`contract_risk_score`, `internet_fiber_flag`, `monthly_charge_ratio`, and `lifetime_value_estimate` are retained for business reporting but are not model features where they duplicate raw fields or depend on a scenario-wide statistic. The model uses a fold-safe preprocessing pipeline.

## Support-ticket proxy

The IBM source does not include support ticket counts. `support_ticket_proxy` is an estimated support-need indicator based on observable service setup and tenure. It is dashboard-only, not an observed operational metric or model input, and should be replaced with actual CRM/support data in production.