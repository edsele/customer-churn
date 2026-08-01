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
- Canonical SHA-256 (LF-normalized): `16320C9C1EC72448DB59AA0A26A0B95401046BEF5D02FD3AEB906448E3055E91`

The checksum normalizes CRLF line endings to LF before hashing, so it remains
stable across normal Git checkouts on different operating systems. The pipeline
records this canonical digest in its run manifest rather than a
platform-specific file-byte hash.

The raw source has 11 blank `TotalCharges` values. They correspond to
zero-tenure/new customer records and are converted during cleaning using
`MonthlyCharges * tenure` (zero for the source rows). The raw file is never
modified by the pipeline.

Duplicate `customerID` values are rejected during validation by default. A
maintainer can opt out explicitly in `config/config.yaml` only when a documented
deduplication policy is appropriate for the input data.

## License and usage

The project code is MIT-licensed. The upstream repository identifies the sample
under the Apache License 2.0; see the [third-party notice](../THIRD_PARTY_NOTICES.md)
for source and license links. The project's MIT license does not supersede or
expand the terms for third-party material. Review the upstream terms and your
organization's data-use requirements before using this project beyond learning
or evaluation work.

## Pipeline outputs

| File | Grain | Purpose |
|---|---|---|
| `processed/customers_clean.csv` | 7,043 observed customers | Validated, deduplicated source snapshot. |
| `processed/customers_analytics_scenario.csv` | 21,000 records | Explicitly labeled scenario for dashboard and SQL prototyping. |
| `processed/customers_features.csv` | 21,000 records | Scenario plus documented engineered features. |
| `processed/customers_scored.csv` | 21,000 records | Scenario plus source-excluded model risk scores. |
| `exports/tableau_dashboard_data.csv` | 21,000 records | Tableau build dataset with presentation labels. |

## Analytics scenario policy

The source dataset does not independently contain 20,000 customers. To support
dashboard prototyping and SQL analysis at a larger record count, the pipeline creates
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
- `lifetime_value_estimate` is current `MonthlyCharges` multiplied by
  `max(72 - tenure, 0)`: a remaining-charge proxy to an assumed 72-month
  horizon. It is not realized revenue, contractual value, or finance-approved
  customer lifetime value.
