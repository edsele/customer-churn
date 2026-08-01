# Technical Notes

## Project summary

This project turns a telecom customer snapshot into a reproducible retention
analytics workflow. It validates and cleans the source data, creates documented
behavioral features, loads a SQLite analytics mart, compares three churn models,
and exports out-of-fold risk scores for a native Power BI report and Tableau-ready
handoff. The business goal is to prioritize human retention outreach by
model-estimated monthly revenue exposure, not to automate customer decisions.

## Design rationale

### Why keep observed and scenario data separate?

The IBM source contains 7,043 observed customers, not 20,000 independent
customers. The project creates a 21,000-row, lineage-labeled scenario for
dashboard and SQL scale, but evaluates the model only on observed source
records. This prevents bootstrap descendants from inflating model performance.

### Why was Gradient Boosting selected?

Gradient Boosting produced the strongest training-only cross-validated ROC-AUC
(0.8499) and a 0.8472 holdout ROC-AUC. The candidate models were close, so the
choice is based on the documented selection metric rather than a broad claim of
superiority. Logistic Regression remains the most interpretable baseline, while
Random Forest is a useful alternative if the business prefers broader outreach
at the cost of more false positives.

### Why optimize ROC-AUC instead of accuracy?

Churn is imbalanced at roughly 26.5%. Accuracy can look favorable simply by
predicting retention for most customers. ROC-AUC evaluates ranking across
thresholds, while precision, recall, F1, and calibration explain what happens
at the chosen operating point.

### Why are dashboard probabilities out-of-fold?

Every customer is scored by a model that did not train on that customer's source
profile. That makes the dashboard's historical risk distribution more credible
than displaying in-sample model probabilities.

### What is `support_ticket_proxy`?

The source does not include support interactions. This field estimates support
need from observable service configuration and tenure; it is never described as
an actual ticket count and should be replaced with CRM/support data in a real
deployment.

### What is `lifetime_value_estimate`?

It is a directional remaining-revenue proxy: current `MonthlyCharges` multiplied
by `max(72 - tenure, 0)`. It is useful for segment planning, but it is not
realized revenue, contractual value, or a finance-approved customer lifetime
value measure.

## Measured results

| Measure | Result |
|---|---:|
| Holdout accuracy | 80.77% |
| Holdout precision | 67.82% |
| Holdout recall | 52.41% |
| Holdout F1 | 59.13% |
| Holdout ROC-AUC | 84.72% |
| Holdout average precision | 66.61% |

The model is most appropriate for ranking and targeting. Threshold selection
should be based on retention capacity, intervention cost, and experimentally
measured campaign uplift rather than a generic performance target.

## Operational considerations

1. Review month-to-month, early-tenure, fiber-optic segments for targeted
   onboarding, contract, and service-experience interventions.
2. Use probability-weighted MRR exposure to sequence outreach, with a human
   review step before any offer or customer treatment.
3. Measure incremental retention with a controlled campaign; correlation in the
   historical snapshot is not evidence that a feature causes churn.
4. Add actual support, CRM, billing-event, and calendar data before production
   deployment, then validate performance temporally.

## Implementation and governance considerations

Raw identifiers and labels are excluded from model features, preprocessing is
fit inside the Scikit-Learn pipeline, parameter tuning uses training folds only,
and the final holdout is not used to select a model.

The dashboard's 0.50 high-risk threshold matches the evaluation-report
classification threshold. In a production setting, it should be reselected
using retention capacity and unit economics.

For production use, replace scenario data with independently observed records,
version the feature contract, schedule data-quality and drift checks, add access
controls, and monitor post-intervention outcomes.
