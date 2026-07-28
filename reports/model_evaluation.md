# Model Evaluation Report

**Selected model:** `gradient_boosting`

## Evaluation protocol

- **Population:** Observed IBM Telco customer snapshots only
- **Holdout:** 20% stratified observed holdout; source groups are kept together when they repeat
- **Selection:** ROC-AUC cross-validation on training data only
- **Classification threshold:** 0.50

## Final holdout metrics

| Metric | Score |
|---|---:|
| Accuracy | 0.8077 |
| Balanced Accuracy | 0.7171 |
| Precision | 0.6782 |
| Recall | 0.5241 |
| F1 | 0.5913 |
| Roc Auc | 0.8472 |
| Average Precision | 0.6661 |

## Candidate comparison (training CV)

These values are from training folds only; the final holdout did not participate in model selection.

| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---:|---:|---:|---:|---:|
| logistic_regression | 0.8074 | 0.6729 | 0.5338 | 0.5948 | 0.8474 |
| random_forest | 0.7693 | 0.5473 | 0.7585 | 0.6356 | 0.8466 |
| gradient_boosting | 0.8074 | 0.6745 | 0.5318 | 0.5943 | 0.8499 |

## Top holdout permutation features

- `tenure`: 0.0528 AUC decrease
- `Contract`: 0.0486 AUC decrease
- `InternetService`: 0.0106 AUC decrease
- `OnlineSecurity`: 0.0068 AUC decrease
- `TotalCharges`: 0.0042 AUC decrease
- `TechSupport`: 0.0041 AUC decrease
- `MonthlyCharges`: 0.0029 AUC decrease
- `PaperlessBilling`: 0.0027 AUC decrease
- `MultipleLines`: 0.0026 AUC decrease
- `payment_risk_flag`: 0.0011 AUC decrease

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