# Model Evaluation Report

**Selected model:** `gradient_boosting`

## Evaluation protocol

- **Population:** Observed IBM Telco customer snapshots only
- **Holdout:** 20% source-disjoint, stratified holdout
- **Selection:** ROC-AUC cross-validation on training data only
- **Classification threshold:** 0.50

## Final holdout metrics

| Metric | Score |
|---|---:|
| Accuracy | 0.8226 |
| Balanced Accuracy | 0.7293 |
| Precision | 0.7824 |
| Recall | 0.5151 |
| F1 | 0.6212 |
| Roc Auc | 0.8692 |
| Average Precision | 0.7310 |

## Candidate comparison (training CV)

These values are from training folds only; the final holdout did not participate in model selection.

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| logistic_regression | 0.8032 | 0.6621 | 0.5006 | 0.5701 | 0.8434 |
| random_forest | 0.7661 | 0.5376 | 0.7395 | 0.6222 | 0.8413 |
| gradient_boosting | 0.7985 | 0.6505 | 0.4926 | 0.5603 | 0.8444 |

## Top holdout permutation features

- `tenure`: 0.0669 AUC decrease
- `Contract`: 0.0523 AUC decrease
- `InternetService`: 0.0102 AUC decrease
- `OnlineSecurity`: 0.0057 AUC decrease
- `TotalCharges`: 0.0043 AUC decrease
- `TechSupport`: 0.0036 AUC decrease
- `MonthlyCharges`: 0.0032 AUC decrease
- `payment_risk_flag`: 0.0014 AUC decrease
- `OnlineBackup`: 0.0014 AUC decrease
- `PaperlessBilling`: 0.0012 AUC decrease

## Business implications

- Use scores to prioritize outreach, not as a standalone cancellation decision. The source is a historical cross-sectional snapshot, so associations are not causal.
- The default threshold favors precision over coverage; test a lower operating threshold only with a defined retention-budget trade-off.
- Positive predictions are concentrated enough to support a targeted offer test, provided campaign uplift is measured experimentally.
- The strongest holdout permutation signals were tenure, Contract, InternetService; investigate them as retention segments rather than causal levers.

## Artifacts

- `reports/figures/roc_curve.png`
- `reports/figures/precision_recall_curve.png`
- `reports/figures/confusion_matrix.png`
- `reports/figures/calibration_curve.png`
- `reports/figures/feature_importance.png`
- `reports/feature_importance.csv`