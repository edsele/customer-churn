# Tableau Dashboard Build Guide

This directory contains the reproducible design specification for the **Customer Churn & Behavioral Analytics** Tableau dashboard. It is intended to be built in Tableau Desktop or Tableau Public from the scored pipeline export.

No Tableau workbook (`.twb`/`.twbx`) or verified Tableau screenshot is
represented as included in this repository. The portable layout preview at
`screenshots/executive_summary_preview.png` is generated with Python from the
scored export; it illustrates the intended composition but is not presented as
a Tableau artifact. Build and export Tableau artifacts only after validating
them against the current scored dataset.

## Purpose

The dashboard helps an executive or retention lead answer three practical questions:

1. How much observed churn and recurring-revenue exposure is present in the selected customer population?
2. Which contracts, lifecycle stages, services, and payment segments are most associated with churn?
3. Which accounts should be reviewed first for a retention intervention?

It deliberately separates **observed churn** (`Churn`) from **predicted churn probability** (`predicted_churn_probability`). The former is a historical outcome; the latter is a model score used to prioritize outreach.

## Data connection

Run the project pipeline first so the scoring export is current, then connect Tableau to:

```text
data/exports/tableau_dashboard_data.csv
```

Use a Tableau extract for the published dashboard. The data is a customer-level snapshot: one row should represent one customer record. `MonthlyCharges` is treated as a monthly recurring revenue (MRR) **proxy**, not a posted finance ledger total.

### Required dashboard data contract

| Field | Tableau role | Use in dashboard | Notes |
|---|---|---|---|
| `customerID` | Dimension / string | Customer counting and action queue | Use `COUNTD`, not `COUNT`, for customer KPIs. |
| `Churn` | Measure / whole number | Observed churn rate | Binary historical label: `1` = churned, `0` = retained. |
| `ChurnLabel` | Dimension / string | Readable observed-churn labels | `Yes` / `No`; use only for presentation. |
| `predicted_churn_probability` | Measure / decimal | Risk distribution, prioritization, revenue at risk | Expected range is 0 to 1; format as a percentage. |
| `risk_band` | Dimension / string | Risk segmentation and filtering | Pipeline-generated categorical band. Standard values are `Low`, `Medium`, and `High`. |
| `support_ticket_proxy` | Measure / whole number | Behavioral-support analysis | **Estimated proxy only**. It is not a count of observed support cases or tickets. |
| `MonthlyCharges` | Measure / decimal | MRR and revenue-at-risk proxies | Format as currency. |
| `lifetime_value_estimate` | Measure / decimal | Remaining-revenue proxy | A 72-month-horizon estimate, not a finance-approved CLV measure. |
| `Contract`, `InternetService`, `PaymentMethod` | Dimensions | Segmentation and global filters | Core operational slices. |
| `tenure`, `tenure_bucket`, `AgeGroup` | Measures / dimensions | Lifecycle and demographic analysis | `AgeGroup` is derived from the senior-citizen indicator. |
| `customer_engagement_score`, `avg_services_purchased` | Measures | Behavioral-driver views | Engineered explanatory features. |
| `record_source` | Dimension | Provenance filter / tooltip | Keep visible when comparing original and augmented scenario records. |

If the three scoring fields—`predicted_churn_probability`, `risk_band`, and `support_ticket_proxy`—are absent, refresh the pipeline output before building. Do not substitute `contract_risk_score` for model probability; it is an engineered rule-based feature, not the scored model output.

### Source scope

Set `record_source` to `observed` by default on the Executive Summary and Churn
Drivers dashboards. This keeps executive KPIs and historical segment findings
anchored to the 7,043 observed source customers. The lineage-labeled scenario
can be explored in a separate prototype view, but it must retain the visible
`record_source` filter and must not be presented as additional observed evidence.

## Build workflow

1. In Tableau, choose **Connect → Text File** and select `tableau_dashboard_data.csv`.
2. Confirm field types in the Data Source pane. In particular, set `Churn` to Number (whole), `predicted_churn_probability` to Number (decimal), and the customer ID and segment fields to String.
3. Create an extract, then hide unused raw fields only after the required calculations have been created.
4. Create the parameter and calculated fields listed in [CALCULATED_FIELDS.md](CALCULATED_FIELDS.md).
5. Build the worksheets in the sequence specified in [DASHBOARD_STORYBOARD.md](DASHBOARD_STORYBOARD.md), then assemble the three dashboards.
6. Add the global filters and dashboard actions described in the storyboard. Apply filters to all relevant worksheets rather than relying on a single sheet's local filter.
7. Perform the quality checks below before publishing or exporting a packaged workbook.

## Data-quality checks in Tableau

Build a small hidden QA worksheet before layout work. It should confirm:

| Check | Expected result |
|---|---|
| Customer grain | `COUNTD([customerID])` is consistent with the pipeline's exported customer count; duplicate IDs are investigated. |
| Observed outcome | `Churn` contains only `0` and `1`; `ChurnLabel` agrees with it. |
| Probability range | `MIN([predicted_churn_probability]) >= 0` and `MAX([predicted_churn_probability]) <= 1`. |
| Scoring completeness | No null probability or `risk_band` values in records intended for risk reporting. |
| Risk bands | Every `risk_band` value is documented and has a valid sort order. |
| Source default | Executive worksheets begin with `record_source = observed`; scenario views disclose their source. |
| Support measure disclosure | Every sheet using `support_ticket_proxy` labels it “Estimated support-contact proxy.” |
| Filter behavior | KPI cards, charts, and the action queue react to the same global segment filters. |

Do not display a churn-rate KPI for a cohort that has no observed churn outcome. In that context, use predicted-risk measures and clearly label them as predictions.

## Recommended workbook organization

| Folder | Contents |
|---|---|
| `00 Parameters` | `Risk Threshold` parameter and optional display settings. |
| `01 KPI` | Customer count, observed churn rate, MRR proxy, remaining-revenue proxy, and high-risk count. |
| `02 Executive` | Contract, tenure, and probability-distribution worksheets. |
| `03 Drivers` | Charges, engagement, service, payment, and support-proxy views. |
| `04 Retention Queue` | Prioritized customer-detail table and revenue-at-risk view. |
| `99 QA` | Validation sheets kept out of the published navigation. |

Use descriptive worksheet names, for example `KPI | Observed Churn Rate` and `Risk | Probability Distribution`, so dashboard maintenance is straightforward.

## Global filters and interaction design

Show these filters in a compact horizontal row on every dashboard:

- `Contract`
- `InternetService`
- `PaymentMethod`
- `AgeGroup`
- `tenure_bucket`
- `risk_band`
- `record_source` with `observed` as the documented executive default

Set the filters to **All using this data source** for the KPI, chart, and action-queue sheets. Add a reset button that returns every filter and the risk threshold to their default state. Contract, tenure, and risk-band marks should also support click-to-filter actions, with a visible “Clear selection” instruction.

## Formatting and accessibility

- Use a 16:9 desktop canvas (recommended: 1,440 × 900 px) and keep KPI cards above the fold.
- Format probabilities and observed churn rates to one decimal place; format currency without unnecessary decimals; show counts with thousands separators.
- Reserve red for observed churn and avoid using color as the only status signal. Suggested risk colors: Low `#15803D`, Medium `#CA8A04`, High `#EA580C`.
- Use a neutral blue such as `#2563EB` for context and an off-white background such as `#F8FAFC`. Retained customers may use muted teal `#0F766E`.
- Add concise subtitles and tooltips that state whether a metric is observed, predicted, estimated, or a proxy.
- Use an accessible sans-serif font, readable axis labels, and direct labels on the most important bars. Avoid red/green-only comparisons.

## Publishing checklist

1. Validate all numbers against the scored export with the same filters applied.
2. Confirm that no chart labels `support_ticket_proxy` as actual support tickets.
3. Check that `predicted_churn_probability` is never averaged or summed without an explicit label explaining the aggregation.
4. Test every filter, action, navigation button, tooltip, and reset control.
5. Review the dashboard at both 1,440 × 900 and a typical laptop resolution.
6. Remove local file paths and unnecessary hidden fields before publishing.
7. Export screenshots only from the verified workbook, name them by dashboard, and record the extract refresh date alongside them.

## Supporting documents

- [Calculated Fields Reference](CALCULATED_FIELDS.md) — exact Tableau calculations, formatting, and caveats.
- [Dashboard Storyboard & Specification](DASHBOARD_STORYBOARD.md) — worksheet-level layout, interactions, and acceptance criteria.
