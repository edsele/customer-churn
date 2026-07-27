# Data Card

## Source dataset

The checked-in raw file, `raw/Telco-Customer-Churn.csv`, is the 7,043-row IBM
Telco Customer Churn sample. It contains a single customer snapshot with
demographics, subscribed services, billing attributes, tenure, and a historical
`Churn` label.

- Source: [IBM Telco Customer Churn repository](https://github.com/IBM/telco-customer-churn-on-icp4d)
- Raw rows: 7,043
- Raw columns: 21
- Positive churn prevalence: 26.54%
- SHA-256: `88BE4B93FBE0CC83421AF1C503794C97C342ECA914C1576DB7C276E61D61358A`

The raw source has 11 blank `TotalCharges` values. They correspond to
zero-tenure/new customer records and are converted during cleaning using
`MonthlyCharges * tenure` (zero for the source rows). The raw file is never
modified by the pipeline.

## License and usage

The project code is MIT-licensed. The dataset remains subject to the source
publisher's terms; the project license does not grant any additional right to
redistribute or commercialize the data. Review the source repository and your
organization's data-use requirements before using this project beyond project
or learning work.

## Pipeline outputs

| File | Grain | Purpose |
|---|---|---|
| `processed/customers_clean.csv` | 7,043 observed customers | Validated, deduplicated source snapshot. |
| `processed/customers_analytics_scenario.csv` | 21,000 records | Explicitly labeled scenario for scalable EDA and dashboard design. |
| `processed/customers_features.csv` | 21,000 records | Scenario plus documented engineered features. |
| `processed/customers_scored.csv` | 21,000 records | Scenario plus out-of-fold model risk scores. |
| `exports/tableau_dashboard_data.csv` | 21,000 records | Tableau-ready scored export with presentation labels. |

## Analytics scenario policy

The source dataset does not independently contain 20,000 customers. To support
the project's large-record EDA and dashboard workflows, the pipeline creates
a 21,000-record **analytics scenario** by sampling within the observed churn
classes and applying bounded, target-independent jitter to tenure and monthly
charges. Each generated row is marked with:

- `record_source`: `observed` or `synthetic_cohort`
- `source_customer_id`: the observed customer profile from which the scenario
  record was derived

Class prevalence is allocated to match the observed source population. Scenario
records are useful for visualization and SQL exercises, but are not additional
independent customers. The default model trains, tunes, and evaluates only on
the 7,043 observed customer snapshots; it never uses scenario descendants as
additional validation evidence.

## Scope and limitations

- The dataset is cross-sectional, not a longitudinal event stream.
- `SeniorCitizen` supports senior-status analysis, not a complete age analysis.
- The source has no actual support tickets. `support_ticket_proxy` is an
  explicitly labeled feature-engineered proxy, not an operational ticket count.
- `MonthlyCharges`, retention, and lifetime-value measures are directional
  snapshot proxies rather than audited revenue or causal estimates.
