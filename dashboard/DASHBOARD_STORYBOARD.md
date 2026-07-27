# Dashboard Storyboard & Specification

This is the implementation specification for the Tableau dashboard. It defines the intended dashboards, worksheets, interactions, and validation criteria; it does not represent a completed Tableau workbook or screenshot.

## Product framing

**Audience:** retention leaders, customer-success managers, and analysts who need a defensible view of observed churn and modeled churn risk.

**Decision supported:** focus retention capacity on segments and accounts where predicted churn exposure and recurring-revenue exposure are highest, while using historical churn to understand the drivers behind that risk.

**Data grain:** one customer record per row. The dashboard is a snapshot analysis, not a time-series revenue ledger.

**Non-negotiable labels:**

- `Churn` / `Observed Churn Rate` = historical outcome.
- `predicted_churn_probability` = model-generated probability score.
- `risk_band` = pipeline-generated risk category.
- `support_ticket_proxy` = **estimated support-contact proxy**, not observed tickets, cases, or workload.
- `MonthlyCharges` = MRR proxy; `lifetime_value_estimate` = remaining-revenue proxy.

## Information architecture

| Dashboard | Primary question | Primary outcome |
|---|---|---|
| 1. Executive Summary | Where is customer and revenue exposure concentrated? | A concise view of churn, MRR proxy, remaining-revenue proxy, and high-risk volume. |
| 2. Churn Drivers & Segments | Which customer segments exhibit the highest observed churn and predicted risk? | Evidence for targeted retention hypotheses. |
| 3. Retention Action Queue | Which accounts and segment plays should be reviewed first? | A filtered, prioritized account list with transparent scoring context. |

Place navigation buttons in the same position on all three pages. Use an executive-neutral title such as **Customer Churn & Behavioral Analytics**, a short subtitle describing the selected population, and a visible reset-filter control.

## Worksheet inventory

| Worksheet name | Dashboard | Mark type | Dimensions | Measures / calculations | Design intent |
|---|---|---|---|---|---|
| `KPI | Customers` | Executive | Text | — | `Customer Count` | Establishes filter-aware population. |
| `KPI | Observed Churn` | Executive | Text | — | `Observed Churn Rate` | Historical outcome, not a model metric. |
| `KPI | MRR Proxy` | Executive | Text | — | `Monthly Recurring Revenue (Proxy)` | Snapshot recurring-charge exposure. |
| `KPI | Remaining-Revenue Proxy` | Executive | Text | — | `Average Remaining-Revenue Proxy (Estimate)` | Directional 72-month-horizon value estimate. |
| `KPI | High-Risk Customers` | Executive | Text | — | `High-Risk Customer Count` | Threshold-driven prioritization volume. |
| `Risk | Probability Distribution` | Executive | Histogram / bars | `Churn Probability Bin (5 pp)` | `Customer Count`; color `risk_band` | Makes score concentration visible without conflating it with actual churn. |
| `Churn | Contract` | Executive, Drivers | Horizontal bars | `Contract` | `Observed Churn Rate`; label `Customer Count` | Shows contract-related observed churn. |
| `Risk | Tenure Stage` | Executive | Lollipop or bar | `tenure_bucket` | `Average Predicted Churn Probability` | Shows lifecycle risk; sort with `Tenure Bucket Sort`. |
| `Churn | Age Group` | Drivers | Horizontal bars | `AgeGroup` | `Observed Churn Rate`; label `Customer Count` | Fulfills the demographic comparison requirement. |
| `Drivers | Payment × Internet` | Drivers | Heatmap | `PaymentMethod`, `InternetService` | `Observed Churn Rate`, `Customer Count` | Reveals operational segment combinations. |
| `Drivers | Engagement vs Risk` | Drivers | Scatterplot | `customer_engagement_score`, `Contract` | `AVG(predicted_churn_probability)`, `Customer Count`, `AVG(MonthlyCharges)` | Tests whether lower engagement aligns with higher modeled risk. |
| `Drivers | Support Proxy` | Drivers | Bars or heatmap | `Support Ticket Proxy Band` | `Observed Churn Rate`, `Customer Count` | Contextual behavioral signal; must carry proxy disclosure. |
| `Risk | Revenue at Risk by Segment` | Retention Queue | Sorted bars | `Contract` or selected segment | `Probability-Weighted MRR at Risk (Estimate)` | Helps size potential retention plays. |
| `Queue | High-Risk Customers` | Retention Queue | Text table | `customerID`, `Contract`, `tenure_bucket`, `risk_band` | probability, `MonthlyCharges`, `Retention Priority Value (Monthly)`, `Support Ticket Proxy Band` | Supports human review and outreach prioritization. |

Refer to [CALCULATED_FIELDS.md](CALCULATED_FIELDS.md) for the exact calculation definitions and formats.

## Dashboard 1 — Executive Summary

**Purpose:** provide an at-a-glance exposure view before the audience drills into drivers or individual accounts.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Customer Churn & Behavioral Analytics    [global filters]       [Reset]     │
│ Population and risk snapshot — observed outcomes and model scores are shown │
├──────────────┬───────────────┬──────────────┬──────────────┬────────────────┤
│ Customers    │ Observed      │ MRR          │ Avg. CLV     │ High-risk      │
│              │ churn rate   │ (proxy)      │ (estimate)   │ customers      │
├────────────────────────────────────┬─────────────────────────────────────────┤
│ Observed churn by contract         │ Predicted churn probability distribution│
│ (rate + customer count)            │ (risk-band color)                       │
├────────────────────────────────────┼─────────────────────────────────────────┤
│ Average predicted risk by tenure   │ Readout / action cue                     │
│ stage                              │ (dynamic text or small KPI)              │
├────────────────────────────────────┴─────────────────────────────────────────┤
│ Footnote: support-contact measure, where used, is an estimated proxy.        │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Build details

| Region | Specification |
|---|---|
| Header | Include dashboard title, a short explanation of selected filters, navigation buttons, and the reset control. Do not use an unsupported “live” refresh claim; show the extract date only when it is actually maintained. |
| KPI row | Use five equal cards. The observed-churn card should be colored neutrally or red only when clearly labeled. The high-risk card must state the active `Risk Threshold`. |
| Contract chart | Horizontal bars sorted descending by `Observed Churn Rate`. Put `Customer Count` in the tooltip to prevent small groups from being over-interpreted. |
| Probability distribution | Use 5 percentage-point bins. The x-axis title is “Predicted churn probability”; color by `risk_band`. Do not title this chart “Churn trend.” |
| Tenure chart | Plot `Average Predicted Churn Probability` by `tenure_bucket`, ordered with `Tenure Bucket Sort`. Use a shared probability axis from 0% to 100% where practical. |
| Narrative | Use a dynamic text object or concise annotation to explain the highest selected segment; it must be reviewed after refresh rather than hard-coded with a stale finding. |

## Dashboard 2 — Churn Drivers & Segments

**Purpose:** move from headline exposure to actionable hypotheses about contracts, demographics, services, payment behavior, engagement, and the estimated support-contact signal.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Churn Drivers & Segments                    [global filters]       [Reset]  │
├────────────────────────────────────┬─────────────────────────────────────────┤
│ Observed churn by age group         │ Observed churn by contract              │
├────────────────────────────────────┼─────────────────────────────────────────┤
│ Payment method × internet service   │ Engagement vs predicted churn probability│
│ (heatmap; show sample size)         │ (scatter; size = customers)              │
├────────────────────────────────────┼─────────────────────────────────────────┤
│ Estimated support-contact proxy     │ Segmented detail / explanatory caption   │
│ band vs observed churn              │                                         │
├────────────────────────────────────┴─────────────────────────────────────────┤
│ Disclosure: proxy is not observed support-case data.                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Build details

| View | Specification | Required tooltip / annotation |
|---|---|---|
| Observed churn by age group | Use horizontal bars with `AgeGroup` on Rows and `Observed Churn Rate` on Columns. | Age group, observed churn rate, customer count, average predicted risk. |
| Observed churn by contract | Reuse the contract worksheet or create a detailed version with `InternetService` as a color or drill-down. | Contract, observed churn rate, customer count, MRR proxy. |
| Payment × internet heatmap | Put `PaymentMethod` on Rows, `InternetService` on Columns, and `Observed Churn Rate` on Color; use `Customer Count` as label or tooltip. | State counts so sparse cells are not over-read. |
| Engagement vs risk | Aggregate to sensible segments (for example `Contract` and `tenure_bucket`) rather than plotting individual customer points. Plot `AVG(customer_engagement_score)` against `Average Predicted Churn Probability`; size marks by `Customer Count`. | Segment name, customers, average engagement, average risk, observed churn rate. |
| Estimated support-contact proxy | Use `Support Ticket Proxy Band` on Rows and `Observed Churn Rate` on Columns. Do not describe the metric as actual ticket volume. | “Estimated support-contact proxy, not observed support cases,” plus count and observed churn rate. |

Avoid causal wording. A segment with higher observed churn or predicted risk is an investigation and prioritization signal, not proof that the characteristic causes churn.

## Dashboard 3 — Retention Action Queue

**Purpose:** convert model output into a transparent, filterable list for human-led retention review.

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Retention Action Queue                         [global filters]    [Reset]  │
├──────────────────────────────┬───────────────────────────────────────────────┤
│ Probability-weighted MRR     │ High-risk MRR proxy by contract / segment     │
│ at risk (estimate)           │                                               │
├──────────────────────────────┴───────────────────────────────────────────────┤
│ [At / above threshold] customer queue                                         │
│ Customer ID | Risk band | Probability | Contract | Tenure | MRR | Priority   │
│             |            |             |          |        |     | value     │
├──────────────────────────────────────────────────────────────────────────────┤
│ Review note: model scores prioritize review; they do not automatically decide│
│ eligibility, pricing, or treatment.                                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Build details

| Region | Specification |
|---|---|
| Exposure KPI | Show `Probability-Weighted MRR at Risk (Estimate)` with a precise title and explanation. It is an expected-exposure estimate, not forecasted booked loss. |
| Segment bar chart | Plot probability-weighted MRR at risk by `Contract` by default. Permit the user to switch the segment with a parameter only if it has been tested and labeled clearly; otherwise use dashboard filters. |
| High-risk filter | Apply `High-Risk Flag (Threshold) = At or Above Threshold` to the queue. Keep the `Risk Threshold` parameter control visible. |
| Queue columns | `customerID`, `risk_band`, `predicted_churn_probability`, `Contract`, `tenure_bucket`, `MonthlyCharges`, `Retention Priority Value (Monthly)`, `Support Ticket Proxy Band`. Sort by priority value descending, then probability descending. |
| Queue tooltips | Explain score, risk-band source, threshold, revenue proxy, and support-proxy disclaimer. Keep the detail view compact; use a max row display and scrolling rather than an unreadable long table. |
| Action language | Frame the output as “review,” “prioritize,” or “consider outreach.” Do not imply automatic denial, eligibility, or pricing decisions. |

## Filters, actions, and navigation

### Global filters

Add `Contract`, `InternetService`, `PaymentMethod`, `AgeGroup`, `tenure_bucket`, and `risk_band` to all relevant worksheets using the same data source. Add `record_source` as a visible provenance filter and set it to `observed` by default on executive and driver views. Keep scenario records in a separately labeled prototype view.

### Dashboard actions

| Action | Source | Target | Behavior |
|---|---|---|---|
| Contract filter | `Churn | Contract` | Executive and Drivers sheets | Selecting a bar filters the selected contract across compatible views. |
| Tenure filter | `Risk | Tenure Stage` | Executive and Retention Queue | Selecting a stage narrows the queue and exposure measures. |
| Risk-band filter | Probability distribution or a dedicated risk-band legend | Retention Queue | Selecting a band filters the action queue; show a clear-selection cue. |
| Navigation | Buttons | The three dashboards | Goes to Executive Summary, Churn Drivers & Segments, or Retention Action Queue. |
| Reset | Reset button | All filters, parameter selections, and action filters | Restores documented default state. |

Test action interaction with ordinary filters. An action should filter the intended targets, not accidentally clear a filter or affect an unrelated QA worksheet.

## Visual and content standards

- Use `risk_band` colors consistently across all pages: Low (green), Medium (amber), High (orange).
- Use a neutral sequential palette for heatmaps. Do not reuse risk colors for an unrelated metric.
- Use direct labels for KPI cards and the most consequential bars; leave detailed values in tooltips where density would suffer.
- Preserve a clear distinction between “observed,” “predicted,” “proxy,” and “estimate” in titles, subtitles, and tooltips.
- Do not put a model-score axis and an observed-churn-rate axis on the same unlabeled scale or dual-axis chart.
- Keep every primary chart interpretable with a color-vision deficiency; include labels or shapes in addition to color where needed.

## Acceptance criteria

The dashboard is ready to publish when all of the following are true:

1. The Executive Summary shows overall observed churn, MRR proxy, remaining-revenue proxy, and high-risk customers, and each KPI responds correctly to global filters.
2. The Drivers page includes churn by age, churn by contract, a churn-probability distribution, and an explicitly disclosed `support_ticket_proxy` view.
3. The Retention Action Queue is driven by `predicted_churn_probability` and `risk_band`, not only by feature-engineered rule scores.
4. Every use of `support_ticket_proxy` says it is an estimated proxy, not an observed support-ticket count.
5. Model probability is formatted as a percentage, remains within 0–100%, and is never labeled as observed churn.
6. Currency measures are labeled as MRR / revenue-at-risk proxies or estimates where appropriate.
7. Contract, service, payment, age, tenure, and risk-band filters operate consistently across their scoped worksheets.
8. Tooltips include enough context to interpret rates: at minimum, customer count and the correct observed/predicted/proxy disclosure.
9. The layout is legible at 1,440 × 900 and includes a working reset control and navigation.
10. Figures are reconciled to the current scored export before screenshots or a packaged workbook are shared.
