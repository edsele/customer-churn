# Model Evaluation Report

**Selected model:** `logistic_regression`

## Evaluation protocol

- **Population:** Observed IBM Telco customer snapshots only
- **Holdout:** 20% source-disjoint, stratified holdout
- **Selection:** ROC-AUC cross-validation on training data only
- **Classification threshold:** 0.50

## Final holdout metrics

| Metric | Score |
|---|---:|
| Accuracy | 0.8197 |
| Balanced Accuracy | 0.7266 |
| Precision | 0.7727 |
| Recall | 0.5126 |
| F1 | 0.6163 |
| Roc Auc | 0.8654 |
| Average Precision | 0.7276 |

## Candidate comparison (training CV)

These values are from training folds only; the final holdout did not participate in model selection.

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| logistic_regression | 0.8062 | 0.6697 | 0.5058 | 0.5762 | 0.8451 |
| random_forest | 0.7689 | 0.5419 | 0.7379 | 0.6245 | 0.8405 |
| gradient_boosting | 0.7996 | 0.6536 | 0.4938 | 0.5623 | 0.8432 |

## Top holdout permutation features

- `tenure`: 0.0365 AUC decrease
- `Contract`: 0.0262 AUC decrease
- `support_ticket_proxy`: 0.0222 AUC decrease
- `support_intensity`: 0.0160 AUC decrease
- `customer_engagement_score`: 0.0129 AUC decrease
- `MultipleLines`: 0.0021 AUC decrease
- `payment_risk_flag`: 0.0018 AUC decrease
- `PhoneService`: 0.0016 AUC decrease
- `tenure_bucket`: 0.0016 AUC decrease
- `InternetService`: 0.0015 AUC decrease

## Business implications

- Use scores to prioritize outreach, not as a standalone cancellation decision. The source is a historical cross-sectional snapshot, so associations are not causal.
- The default threshold favors precision over coverage; test a lower operating threshold only with a defined retention-budget trade-off.
- Positive predictions are concentrated enough to support a targeted offer test, provided campaign uplift is measured experimentally.
- The strongest holdout permutation signals were tenure, Contract, support_ticket_proxy; investigate them as retention segments rather than causal levers.

## Artifacts

- `reports/figures/roc_curve.png`
- `reports/figures/precision_recall_curve.png`
- `reports/figures/confusion_matrix.png`
- `reports/figures/calibration_curve.png`
- `reports/figures/feature_importance.png`
- `reports/feature_importance.csv`