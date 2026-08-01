# Tableau Calculated Fields Reference

This reference uses the customer-level scored export described in [README.md](README.md). Create calculations with the exact names below so worksheet instructions remain reusable.

## Calculation conventions

- The export grain is one row per `customerID`. Customer-facing KPIs still use `COUNTD([customerID])` as a guard against accidental duplication.
- `Churn` is an **observed historical outcome**. `predicted_churn_probability` is a **model score**. Do not substitute one for the other.
- `support_ticket_proxy` is an **estimated behavioral proxy**, not observed case-management data. Include that wording in every supporting tooltip or subtitle.
- `risk_band` and `HighRiskFlag` come from the scoring pipeline and are the reporting dimensions of record. They use the unrounded model probability; `predicted_churn_probability` is a four-decimal presentation field. The interactive threshold parameter below is only for what-if prioritization and should not silently rewrite the pipeline's banding.

## Source scope

Apply `record_source = "observed"` as the default filter to Executive Summary
and Churn Drivers worksheets. This keeps historical KPIs and segment findings
anchored to observed customers. If a separate scenario prototype is shown,
leave `record_source` visible and label the view as a scenario.

## Parameter

Create this parameter before the dependent fields.

| Parameter | Data type | Allowable values | Current value | Purpose |
|---|---|---|---|---|
| `Risk Threshold` | Float | Range: 0.10–0.90, step 0.05 | 0.50 | Defines which scored customers appear in the high-risk KPI and retention queue. |

Format the parameter control as a percentage. The default should match the current model-operating threshold documented by the pipeline owner. If it is changed for a what-if view, retain an on-screen note that the change affects prioritization, not model performance.

## Core KPI fields

### `Customer Count`

```tableau
COUNTD([customerID])
```

Format: whole number. Use as the denominator for customer-level rates.

### `Churned Customers`

```tableau
COUNTD(
    IF [Churn] = 1 THEN [customerID] END
)
```

Format: whole number. This counts observed churned customers, not customers above the model threshold.

### `Observed Churn Rate`

```tableau
[Churned Customers] / [Customer Count]
```

Format: percentage, one decimal place. Use this on charts labeled “Observed churn,” including the churn-by-contract and churn-by-age views.

### `Retention Rate`

```tableau
1 - [Observed Churn Rate]
```

Format: percentage, one decimal place.

### `Monthly Recurring Revenue (Proxy)`

```tableau
SUM([MonthlyCharges])
```

Format: currency, zero decimals. This represents the sum of customer monthly charges in the selected snapshot; it is not a general-ledger revenue total.

### `Average Remaining-Revenue Proxy (Estimate)`

```tableau
AVG([lifetime_value_estimate])
```

Format: currency, zero decimals. This is `MonthlyCharges x max(72 - tenure, 0)`, a directional 72-month-horizon remaining-revenue estimate, not a finance-approved customer lifetime value measure.

## Risk and revenue-at-risk fields

### `High-Risk Flag (Threshold)`

```tableau
IF ISNULL([predicted_churn_probability]) THEN "Unscored"
ELSEIF [predicted_churn_probability] >= [Risk Threshold] THEN "At or Above Threshold"
ELSE "Below Threshold"
END
```

Format: discrete dimension. Use for retention-queue filters and labels. It intentionally uses model probability, not `contract_risk_score`.

### `High-Risk Customer Count`

```tableau
COUNTD(
    IF [predicted_churn_probability] >= [Risk Threshold]
    THEN [customerID]
    END
)
```

Format: whole number. Subtitle: “Customers with predicted churn probability at or above the selected threshold.”

### `High-Risk MRR (Proxy)`

```tableau
SUM(
    IF [predicted_churn_probability] >= [Risk Threshold]
    THEN [MonthlyCharges]
    ELSE 0
    END
)
```

Format: currency, zero decimals. This is the snapshot MRR proxy held by accounts above the selected threshold.

### `Probability-Weighted MRR at Risk (Estimate)`

```tableau
SUM([MonthlyCharges] * [predicted_churn_probability])
```

Format: currency, zero decimals. This is an expected monthly exposure estimate, useful for comparing segments; it is not a forecast of booked loss.

### `Average Predicted Churn Probability`

```tableau
AVG([predicted_churn_probability])
```

Format: percentage, one decimal place. Always label it “Average predicted churn probability,” not “churn rate.”

### `Retention Priority Value (Monthly)`

```tableau
[MonthlyCharges] * [predicted_churn_probability]
```

Format: currency, zero decimals. This row-level estimate ranks the retention queue by expected monthly revenue exposure. Sort descending after filtering to `High-Risk Flag (Threshold) = At or Above Threshold`.

## Risk-band and distribution fields

### `Risk Band Sort`

```tableau
CASE UPPER([risk_band])
    WHEN "LOW" THEN 1
    WHEN "MEDIUM" THEN 2
    WHEN "HIGH" THEN 3
    ELSE 99
END
```

Format: whole number, hidden from the published view. Sort `risk_band` ascending by this field. If the scoring pipeline uses a different band vocabulary, update this mapping once and document the change in the workbook description.

### `Churn Probability Bin (5 pp)`

```tableau
IF ISNULL([predicted_churn_probability]) THEN NULL
ELSEIF [predicted_churn_probability] = 1 THEN 0.95
ELSE FLOOR([predicted_churn_probability] * 20) / 20
END
```

Format: percentage, zero decimals. Place this field on Columns as a discrete or continuous field for the probability-distribution chart. The explicit `1` case keeps a score of 100% in the final 95–100% bin.

### `Churn Probability Bin Label`

```tableau
IF ISNULL([Churn Probability Bin (5 pp)]) THEN "Unscored"
ELSE
    STR(INT([Churn Probability Bin (5 pp)] * 100))
    + "%–"
    + STR(INT(([Churn Probability Bin (5 pp)] + 0.05) * 100))
    + "%"
END
```

Format: discrete dimension. Use in tooltips or when an executive audience benefits from readable bin labels.

## Behavioral and lifecycle fields

### `Support Ticket Proxy Band`

```tableau
IF ISNULL([support_ticket_proxy]) THEN "Not available"
ELSEIF [support_ticket_proxy] <= 1 THEN "0–1"
ELSEIF [support_ticket_proxy] <= 3 THEN "2–3"
ELSEIF [support_ticket_proxy] <= 5 THEN "4–5"
ELSE "6+"
END
```

Format: discrete dimension. Label the related worksheet **“Estimated support-contact proxy”**. Do not call this field “support tickets,” “support volume,” or “case count” without the proxy qualifier.

### `Average Support Ticket Proxy`

```tableau
AVG([support_ticket_proxy])
```

Format: number, one decimal place. Use only to compare relative proxy intensity across segments; it should not be interpreted as operational workload.

### `Tenure Bucket Sort`

```tableau
IF [tenure] <= 6 THEN 1
ELSEIF [tenure] <= 24 THEN 2
ELSEIF [tenure] <= 48 THEN 3
ELSE 4
END
```

Format: whole number, hidden. Sort `tenure_bucket` ascending by this field so lifecycle stages remain chronological.

### `Observed Churn Status`

```tableau
IF [Churn] = 1 THEN "Churned"
ELSEIF [Churn] = 0 THEN "Retained"
ELSE "Unknown"
END
```

Format: discrete dimension. This can be used where a readable observed-outcome field is required; prefer `ChurnLabel` if it is already complete and validated.

## Recommended tooltip text

Use a consistent disclosure in views that include risk or support behavior:

```text
Observed churn rate is based on historical Churn labels.
Predicted churn probability is a model score used for prioritization.
Support-contact value is an estimated proxy, not observed support cases.
```

For a high-risk customer table, show `customerID`, `Contract`, `tenure`, `MonthlyCharges`, `predicted_churn_probability`, `risk_band`, `Retention Priority Value (Monthly)`, and `Support Ticket Proxy Band`. Do not place the raw `support_ticket_proxy` next to language that suggests actual support case counts.

## Guardrails

| Do | Avoid |
|---|---|
| Use `COUNTD([customerID])` for customer counts. | Counting rows if the data grain changes. |
| Call `[Observed Churn Rate]` an observed outcome. | Calling average probability a churn rate. |
| Use `risk_band` for segment reporting and the threshold parameter for what-if prioritization. | Rebuilding a conflicting risk-band taxonomy in multiple worksheets. |
| Label revenue measures as MRR or revenue-at-risk proxies / estimates. | Presenting `MonthlyCharges` as audited revenue. |
| Call the support metric an estimated proxy in subtitles and tooltips. | Presenting `support_ticket_proxy` as an actual support-system metric. |
