# Power BI Measure Reference

All measures use the `customer_churn_observed_dashboard` table, which contains
only observed customer records. Display measures are kept separate from numeric
measures so charts retain numeric aggregation behavior.

```DAX
Customer Count =
DISTINCTCOUNT ( 'customer_churn_observed_dashboard'[customerID] )

Churned Customers =
CALCULATE ( [Customer Count], 'customer_churn_observed_dashboard'[Churn] = 1 )

Observed Churn Rate =
DIVIDE ( [Churned Customers], [Customer Count] )

Retention Rate =
1 - [Observed Churn Rate]

Monthly Revenue Proxy =
SUM ( 'customer_churn_observed_dashboard'[MonthlyCharges] )

Revenue at Risk =
SUM ( 'customer_churn_observed_dashboard'[revenue_at_risk] )

High-Risk Customers =
SUM ( 'customer_churn_observed_dashboard'[HighRiskFlag] )

High-Risk MRR Proxy =
SUM ( 'customer_churn_observed_dashboard'[high_risk_mrr_proxy] )

Average Predicted Churn Probability =
AVERAGE ( 'customer_churn_observed_dashboard'[predicted_churn_probability] )

Average Remaining-Revenue Proxy =
AVERAGE ( 'customer_churn_observed_dashboard'[lifetime_value_estimate] )

High-Risk Customer Share =
DIVIDE ( [High-Risk Customers], [Customer Count] )
```

The following display measures drive the executive KPI card. They format a
numeric base measure for presentation only and should not be reused as chart
axes or numerical inputs.

```DAX
Customer Count KPI = FORMAT ( [Customer Count], "#,0" )
Observed Churn Rate KPI = FORMAT ( [Observed Churn Rate], "0.0%" )
Monthly Revenue KPI = FORMAT ( [Monthly Revenue Proxy], "$#,##0" )
Revenue at Risk KPI = FORMAT ( [Revenue at Risk], "$#,##0" )
High-Risk Customers KPI = FORMAT ( [High-Risk Customers], "#,0" )
Predicted Risk KPI = FORMAT ( [Average Predicted Churn Probability], "0.0%" )
Average Remaining Revenue KPI = FORMAT ( [Average Remaining-Revenue Proxy], "$#,##0" )
```

`HighRiskFlag` is generated from the reproducible model decision threshold in
`config/config.yaml` (currently 0.50). It is intentionally not portrayed as a
causal treatment recommendation.
