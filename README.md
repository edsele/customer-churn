# Customer Churn & Behavioral Analytics

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC)](tests/)
[![Style](https://img.shields.io/badge/style-ruff-261230)](https://docs.astral.sh/ruff/)
[![License: MIT](https://img.shields.io/badge/License-MIT-16A34A.svg)](LICENSE)

An end-to-end analytics and machine-learning project for identifying telecom
churn risk, understanding behavioral segments, and prioritizing retention
opportunities. The project pairs a validated Python pipeline with a SQLite data
mart, 14 analytical SQL queries, model diagnostics, and a Tableau-ready
customer-level export.

> **Evidence first:** the IBM source contains 7,043 observed customers. This
> repository also creates a clearly labeled 21,000-row analytics scenario for
> scalable EDA and dashboard design. The model is trained and evaluated only on
> the 7,043 observed source records—scenario rows are not treated as independent
> evidence.

![Executive dashboard preview](dashboard/screenshots/executive_summary_preview.png)

*Portable executive-layout preview generated from the scored export. It is not
represented as a Tableau screenshot or workbook; see [`dashboard/`](dashboard/)
for the verified Tableau build specification and calculated fields.*

## Business problem

Customer churn erodes recurring revenue and raises acquisition costs. A
retention team needs more than a historical churn rate: it needs a defensible
way to identify segments worth investigating, rank accounts for human review,
and measure whether an intervention actually changes outcomes.

This project answers the following questions:

1. Which customer, contract, service, and payment segments exhibit the highest
   observed churn?
2. Which snapshot attributes are most useful for ranking churn risk?
3. Where is probability-weighted monthly revenue exposure concentrated?
4. How can an executive dashboard distinguish observed outcomes from predicted
   risk, estimates, and operational proxies?

## Results at a glance

The current reproducible run selected logistic regression by **training-only
cross-validated ROC-AUC**. It was then evaluated once on a source-disjoint 20%
holdout of the observed IBM customer records.

| Metric | Holdout result |
|---|---:|
| Accuracy | 81.97% |
| Precision | 77.27% |
| Recall | 51.26% |
| F1 | 61.63% |
| ROC-AUC | **86.54%** |
| Average precision | 72.76% |

Candidate comparison on training folds:

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| Logistic Regression | 80.62% | 66.97% | 50.58% | 57.62% | **84.51%** |
| Random Forest | 76.89% | 54.19% | 73.79% | **62.45%** | 84.05% |
| Gradient Boosting | 79.96% | 65.36% | 49.38% | 56.23% | 84.32% |

The model's **86.5% ROC-AUC** means it separates observed churners and
non-churners well enough for risk ranking. Its 82.0% threshold accuracy is
reported honestly; it is not inflated with scenario descendants or target-derived
features. See the generated [model evaluation report](reports/model_evaluation.md)
for the protocol, cross-validation results, confusion matrix, calibration curve,
and feature importance.

### Key EDA findings

- Overall observed churn is **26.5%** in the 21,000-record analytics scenario,
  which preserves the 7,043-record source prevalence.
- Month-to-month customers show the highest observed churn (**42.7%**), followed
  by fiber-optic customers (**41.8%**) and electronic-check payers (**45.2%**).
- Customers in their first six months show **53.2%** observed churn versus
  **14.0%** for customers beyond 24 months.
- Tenure, contract type, and the documented estimated support-need proxy are
  the strongest holdout permutation signals. They are prioritization signals,
  not causal claims.

## Architecture

```text
IBM Telco customer snapshot (7,043 observed records)
                         |
                         v
       schema validation + cleaning + audit JSON
                         |
          +--------------+---------------------+
          |                                    |
          v                                    v
observed cleaned data                  21,000-row analytics scenario
          |                             (lineage-labeled; EDA/dashboard)
          +--------------------+---------------+
                               |
                               v
                documented feature engineering
                               |
          +--------------------+---------------------+
          |                                          |
          v                                          v
  observed-only CV / holdout                  EDA + SQLite data mart
          |                                          |
          v                                          v
  trained model + diagnostics        scored Tableau export + SQL reporting
          |
          v
out-of-fold probabilities for every scenario record
```

## Dataset and provenance

The raw input is the IBM Telco Customer Churn sample: 7,043 customer snapshots,
21 columns, and a `Churn` outcome. The source has no dates, event history,
actual age, or actual support-ticket counts.

| Attribute | Detail |
|---|---|
| Source | [IBM Telco Customer Churn](https://github.com/IBM/telco-customer-churn-on-icp4d) |
| Observed customers | 7,043 |
| Analytics scenario | 21,000 rows: 7,043 observed + 13,957 labeled synthetic cohort records |
| Target | `Churn` (`1` = churned, `0` = retained) |
| Source prevalence | 26.54% churn |
| Raw file checksum | SHA-256 `88BE4B93FBE0CC83421AF1C503794C97C342ECA914C1576DB7C276E61D61358A` |

Read the [data card](data/README.md) for data handling, source terms, scenario
policy, lineage fields, and limitations.

### Why an analytics scenario exists

The project needs a 20,000+ record analytics surface without falsely claiming
that 20,000 independent customers were observed. The scenario samples within
the observed churn classes, applies small bounded perturbations to tenure and
monthly charges, maintains source-compatible charge logic, and carries both
`record_source` and `source_customer_id`. The default model excludes those
derived rows from training and evaluation.

## Project structure

```text
customer-churn/
├── config/
│   └── config.yaml                 # paths, validation, augmentation, modeling settings
├── data/
│   ├── README.md                   # provenance and data-use notes
│   ├── raw/                        # checked-in IBM source CSV
│   ├── processed/                  # generated clean, feature, score, and SQLite artifacts
│   └── exports/                    # generated Tableau-ready CSV
├── dashboard/
│   ├── README.md                   # Tableau build and QA guide
│   ├── CALCULATED_FIELDS.md        # exact Tableau calculations
│   ├── DASHBOARD_STORYBOARD.md     # three-page dashboard specification
│   └── screenshots/                # portable preview / verified workbook captures
├── models/                         # generated fitted pipelines and metrics JSON
├── notebooks/                      # optional interactive EDA companion
├── reports/
│   ├── figures/                    # EDA and evaluation plots
│   ├── data_quality_report.json
│   ├── eda_summary.md
│   ├── feature_engineering.md
│   ├── model_evaluation.md
│   └── run_manifest.json
├── sql/                             # SQLite views and 14 reusable analytical queries
├── src/                             # production pipeline modules
├── tests/                           # unit and integration tests
├── run_pipeline.py                  # pipeline CLI
├── run_sql.py                       # SQL query runner
├── requirements.txt
└── pyproject.toml
```

## Quick start

### 1. Install

```bash
git clone https://github.com/<your-username>/customer-churn-analytics.git
cd customer-churn-analytics

python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Build the full project

```bash
python run_pipeline.py
```

This single command:

1. loads and validates the raw file;
2. cleans missing values and duplicate IDs;
3. creates the lineage-labeled 21,000-row analytics scenario;
4. engineers documented features and exports a data-quality audit;
5. tunes Logistic Regression, Random Forest, and Gradient Boosting on observed
   training folds only;
6. evaluates the selected model once on the held-out observed customers;
7. creates out-of-fold probabilities for dashboard records;
8. writes the SQLite mart, Tableau export, EDA figures, diagnostics, and preview.

For a data-only run:

```bash
python run_pipeline.py --skip-training
```

### 3. Run checks

```bash
python -m pytest -q
python -m ruff check .
```

## Data pipeline

The pipeline is deliberately modular and testable.

| Module | Responsibility |
|---|---|
| `src/preprocessing.py` | Raw loading, schema/range checks, de-duplication, numeric coercion, cleaning, scenario lineage, and audit JSON. |
| `src/feature_engineering.py` | Snapshot-safe feature creation, feature documentation, and fold-safe preprocessing. |
| `src/modeling.py` | Source-disjoint observed holdout, `GridSearchCV` / `RandomizedSearchCV`, model persistence, and out-of-fold scoring. |
| `src/evaluation.py` | Classification metrics, CV summaries, ROC/PR/calibration curves, confusion matrix, and holdout permutation importance. |
| `src/database.py` | SQLite customer and prediction tables, analytical views, and Tableau export. |
| `src/eda.py` | Repeatable visual EDA and values-driven summary. |
| `src/dashboard_preview.py` | Portable executive layout preview from the scored data contract. |

The current data-quality audit is available at
[`reports/data_quality_report.json`](reports/data_quality_report.json). It
records 7,043 inputs, zero duplicate IDs, zero invalid churn labels, and a
scenario churn-rate delta of roughly 0.001 percentage points.

## Feature engineering

| Feature | Purpose |
|---|---|
| `tenure_bucket` | Groups lifecycle into onboarding, growth, mature, and loyal stages. |
| `revenue_per_month` | Realized charge rate; uses monthly charges for zero-tenure records. |
| `service_count` / `avg_services_purchased` | Counts active service subscriptions. |
| `contract_risk_score` | Business-facing contract-flexibility indicator for reporting. |
| `customer_engagement_score` | Explainable service, tenure, security, and contract composite. |
| `payment_risk_flag` | Electronic-check indicator. |
| `support_ticket_proxy` | Estimated support need from observable service setup and tenure—not actual ticket data. |
| `support_intensity` | Support proxy normalized by tenure. |
| `lifetime_value_estimate` | Directional 72-month-horizon value estimate for reporting. |

The full definitions, intended use, and model boundary are in
[`reports/feature_engineering.md`](reports/feature_engineering.md). Features
that duplicate raw categories or depend on a scenario-wide statistic are kept
for business reporting but excluded from the model input.

## Machine learning methodology

### Validation design

- **Population:** the original observed IBM records only.
- **Holdout:** deterministic 20% stratified, source-disjoint partition.
- **Tuning:** 5-fold `StratifiedGroupKFold` on training records only, optimizing
  ROC-AUC.
- **Models:** Logistic Regression, Random Forest, and Gradient Boosting;
  XGBoost is supported as an optional configuration choice.
- **Preprocessing:** `ColumnTransformer` pipeline with training-fold median /
  most-frequent imputation, standard scaling, and one-hot encoding.
- **Final evaluation:** exactly one evaluation of the selected model on the
  untouched holdout. Candidate comparison in the report is training-CV only.
- **Dashboard scores:** five-fold out-of-fold probabilities so a source profile
  is scored by a model that did not train on that source.

### Evaluation artifacts

| Artifact | What it shows |
|---|---|
| `reports/figures/roc_curve.png` | Ranking discrimination across thresholds. |
| `reports/figures/precision_recall_curve.png` | Positive-class performance under churn imbalance. |
| `reports/figures/confusion_matrix.png` | Classification outcomes at the documented 0.50 threshold. |
| `reports/figures/calibration_curve.png` | Alignment of predicted probability and observed rate. |
| `reports/figures/feature_importance.png` | Holdout permutation importance, measured as ROC-AUC decrease. |
| `reports/feature_importance.csv` | Exportable numeric feature-importance table. |

## SQL analytics

The SQLite mart contains two tables:

- `customers`: feature-engineered customer snapshot;
- `customer_predictions`: model name/version, out-of-fold churn probability,
  risk band, threshold, scoring source, and probability-weighted MRR exposure.

`sql/00_create_views.sql` creates a canonical reporting view plus segment,
high-risk worklist, and retention-snapshot views. The remaining 14 scripts
cover churn segments, contract revenue, lifetime/tenure, high-risk groups, MRR
exposure, retention snapshots, payment methods, senior-status demographics,
support-proxy segments, value segments, risk worklists, score distribution,
scoring coverage, and executive KPIs.

```bash
# Run all reporting queries after the pipeline
python run_sql.py

# Run one query
python run_sql.py --query 04_high_risk_customer_groups.sql
```

The source is a snapshot, so “retention” is a retained-share proxy by tenure
segment and “monthly revenue analysis” refers to snapshot MRR exposure—not a
fabricated time series.

## Tableau dashboard

The Tableau-ready export is generated at
`data/exports/tableau_dashboard_data.csv`. It includes `Churn` and
`ChurnLabel` for observed outcomes, `predicted_churn_probability` and
`risk_band` for model scores, revenue-at-risk estimates, customer lifecycle,
and lineage fields.

The dashboard specification defines three pages:

1. **Executive Summary** — observed churn, MRR proxy, estimated CLV, high-risk
   customers, probability distribution, and revenue-at-risk exposure.
2. **Churn Drivers & Segments** — senior status, contract, payment/service,
   lifecycle, engagement, and explicitly disclosed support-proxy views.
3. **Retention Action Queue** — filterable human-review worklist ranked by
   probability-weighted monthly revenue exposure.

Use these companion documents to build and verify the interactive Tableau
workbook:

- [Tableau build guide](dashboard/README.md)
- [Calculated fields](dashboard/CALCULATED_FIELDS.md)
- [Dashboard storyboard](dashboard/DASHBOARD_STORYBOARD.md)

Every view must distinguish **observed**, **predicted**, **estimated**, and
**proxy** measures. Interactive global filters cover contract, internet service,
payment method, senior status, lifecycle stage, risk band, and source lineage.


## Limitations and future work

- Replace the scenario data with a larger, independently observed labeled source
  before making claims about 20,000 real customers.
- Integrate actual CRM, support, and billing-event data; retire the support proxy.
- Add temporal validation once churn events and observation dates are available.
- Calibrate thresholds against intervention cost, contact capacity, and measured
  campaign uplift instead of a generic 0.60 high-risk cutoff.
- Add drift monitoring, data contracts, and scheduled orchestration for a
  production deployment.
- Use treatment-effect or uplift modeling after collecting randomized retention
  campaign outcomes.

## License

Project code is available under the [MIT License](LICENSE). Dataset use remains
subject to the original source terms described in the [data card](data/README.md).
