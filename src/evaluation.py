"""Holdout evaluation, cross-validation summaries, and model diagnostics."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.calibration import calibration_curve
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline

from src.config import load_config, resolve_path

if TYPE_CHECKING:
    from src.modeling import ModelResult

logger = logging.getLogger(__name__)

plt.style.use("seaborn-v0_8-whitegrid")


def compute_metrics(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray,
    y_proba: np.ndarray | None = None,
) -> dict[str, float]:
    """Calculate threshold and probability metrics for positive-class churn."""
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    if y_proba is not None:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba))
        metrics["average_precision"] = float(average_precision_score(y_true, y_proba))
    return metrics


def run_cross_validation(
    pipeline: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series | None = None,
) -> dict[str, dict[str, Any]]:
    """Run deterministic CV on training data and return mean, deviation, and folds."""
    config = load_config()
    folds = min(int(config["modeling"]["cv_folds"]), len(X))
    if folds < 2:
        raise ValueError("At least two observations are required for cross-validation.")
    if groups is not None:
        cv = StratifiedGroupKFold(
            n_splits=min(folds, int(groups.nunique())),
            shuffle=True,
            random_state=config["project"]["random_seed"],
        )
    else:
        cv = StratifiedKFold(
            n_splits=folds,
            shuffle=True,
            random_state=config["project"]["random_seed"],
        )
    scoring = [
        "accuracy",
        "balanced_accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "average_precision",
    ]
    result = cross_validate(
        pipeline,
        X,
        y,
        cv=cv,
        groups=groups,
        n_jobs=config["modeling"]["n_jobs"],
        return_train_score=False,
        scoring=scoring,
    )
    return {
        metric: {
            "mean": float(np.mean(result[f"test_{metric}"])),
            "std": float(np.std(result[f"test_{metric}"])),
            "scores": [float(value) for value in result[f"test_{metric}"]],
        }
        for metric in scoring
    }


def plot_roc_curve(
    y_true: np.ndarray | pd.Series,
    y_proba: np.ndarray,
    output_path: Path,
) -> Path:
    """Generate and save a holdout ROC curve."""
    false_positive_rate, true_positive_rate, _ = roc_curve(y_true, y_proba)
    score = roc_auc_score(y_true, y_proba)
    figure, axis = plt.subplots(figsize=(8, 6))
    axis.plot(
        false_positive_rate,
        true_positive_rate,
        color="#2563eb",
        linewidth=2,
        label=f"ROC-AUC = {score:.3f}",
    )
    axis.plot([0, 1], [0, 1], color="#94a3b8", linestyle="--", linewidth=1)
    axis.set(xlabel="False positive rate", ylabel="True positive rate")
    axis.set_title("Holdout ROC Curve — Churn Prediction")
    axis.legend(loc="lower right")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return output_path


def plot_precision_recall_curve(
    y_true: np.ndarray | pd.Series,
    y_proba: np.ndarray,
    output_path: Path,
) -> Path:
    """Generate and save a holdout precision-recall curve."""
    precision, recall, _ = precision_recall_curve(y_true, y_proba)
    average_precision = average_precision_score(y_true, y_proba)
    figure, axis = plt.subplots(figsize=(8, 6))
    axis.plot(
        recall,
        precision,
        color="#059669",
        linewidth=2,
        label=f"Average precision = {average_precision:.3f}",
    )
    axis.set(xlabel="Recall", ylabel="Precision")
    axis.set_title("Holdout Precision–Recall Curve — Churn Prediction")
    axis.legend(loc="lower left")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return output_path


def plot_confusion_matrix(
    y_true: np.ndarray | pd.Series,
    y_pred: np.ndarray,
    output_path: Path,
) -> Path:
    """Generate and save a labeled holdout confusion matrix."""
    matrix = confusion_matrix(y_true, y_pred)
    figure, axis = plt.subplots(figsize=(6, 5))
    sns.heatmap(
        matrix,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Retained", "Churned"],
        yticklabels=["Retained", "Churned"],
        ax=axis,
    )
    axis.set(xlabel="Predicted", ylabel="Actual", title="Holdout Confusion Matrix")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return output_path


def plot_calibration_curve(
    y_true: np.ndarray | pd.Series,
    y_proba: np.ndarray,
    output_path: Path,
) -> Path:
    """Plot the relationship between predicted and observed churn rates."""
    observed_rate, predicted_rate = calibration_curve(y_true, y_proba, n_bins=10)
    figure, axis = plt.subplots(figsize=(7, 6))
    axis.plot([0, 1], [0, 1], "--", color="#94a3b8", label="Ideal calibration")
    axis.plot(
        predicted_rate,
        observed_rate,
        marker="o",
        color="#7c3aed",
        label="Model",
    )
    axis.set(xlabel="Mean predicted probability", ylabel="Observed churn rate")
    axis.set_title("Holdout Probability Calibration")
    axis.legend(loc="upper left")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return output_path


def compute_feature_importance(
    pipeline: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
) -> pd.DataFrame:
    """Measure raw-feature importance by holdout permutation AUC decrease."""
    config = load_config()
    result = permutation_importance(
        pipeline,
        X,
        y,
        n_repeats=12,
        n_jobs=config["modeling"]["n_jobs"],
        random_state=config["project"]["random_seed"],
        scoring="roc_auc",
    )
    return (
        pd.DataFrame(
            {
                "feature": X.columns,
                "importance_mean": result.importances_mean,
                "importance_std": result.importances_std,
            }
        )
        .sort_values("importance_mean", ascending=False)
        .reset_index(drop=True)
    )


def plot_feature_importance(
    importance: pd.DataFrame,
    output_path: Path,
    top_n: int = 20,
) -> Path:
    """Render a concise bar chart of holdout permutation importance."""
    plot_data = importance.head(top_n).sort_values("importance_mean")
    figure, axis = plt.subplots(figsize=(10, 8))
    axis.barh(plot_data["feature"], plot_data["importance_mean"], color="#7c3aed")
    axis.set(xlabel="Mean ROC-AUC decrease", title="Holdout Permutation Importance")
    figure.tight_layout()
    figure.savefig(output_path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return output_path


def generate_evaluation_report(
    pipeline: Pipeline,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    model_name: str,
    candidate_results: dict[str, ModelResult] | None = None,
    training_cv: dict[str, dict[str, Any]] | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Evaluate the selected model exactly once on the untouched holdout.

    Candidate selection is supplied separately as training-only cross-validation
    evidence.  This function deliberately does not refit or tune on the holdout.
    """
    config = load_config()
    figures_dir = output_dir or resolve_path(config["paths"]["figures_dir"])
    figures_dir.mkdir(parents=True, exist_ok=True)
    reports_dir = resolve_path("reports")
    reports_dir.mkdir(parents=True, exist_ok=True)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    metrics = compute_metrics(y_test, y_pred, y_proba)
    importance = compute_feature_importance(pipeline, X_test, y_test)
    importance.to_csv(reports_dir / "feature_importance.csv", index=False)

    plot_roc_curve(y_test, y_proba, figures_dir / "roc_curve.png")
    plot_precision_recall_curve(y_test, y_proba, figures_dir / "precision_recall_curve.png")
    plot_confusion_matrix(y_test, y_pred, figures_dir / "confusion_matrix.png")
    plot_calibration_curve(y_test, y_proba, figures_dir / "calibration_curve.png")
    plot_feature_importance(importance, figures_dir / "feature_importance.png")

    candidates = _serialize_candidates(candidate_results)
    report = {
        "model_name": model_name,
        "evaluation_protocol": {
            "population": "Observed IBM Telco customer snapshots only",
            "holdout": "20% source-disjoint, stratified holdout",
            "selection": "ROC-AUC cross-validation on training data only",
            "threshold": 0.5,
        },
        "holdout_metrics": metrics,
        "training_cross_validation": training_cv or {},
        "candidate_comparison": candidates,
        "classification_report": classification_report(y_test, y_pred, output_dict=True),
        "top_permutation_features": importance.head(10).to_dict(orient="records"),
        "business_implications": _business_implications(metrics, importance),
    }
    json_path = reports_dir / "model_evaluation.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    markdown_path = reports_dir / "model_evaluation.md"
    markdown_path.write_text(_format_report_markdown(report), encoding="utf-8")
    logger.info("Saved holdout evaluation report to %s", markdown_path)
    return report


def _serialize_candidates(
    candidates: dict[str, ModelResult] | None,
) -> dict[str, dict[str, float]]:
    """Condense candidate CV metrics for JSON and Markdown reporting."""
    if not candidates:
        return {}
    comparison: dict[str, dict[str, float]] = {}
    for name, result in candidates.items():
        comparison[name] = {
            metric: float(summary["mean"])
            for metric, summary in result.cv_metrics.items()
        }
        comparison[name]["selection_roc_auc"] = float(result.selection_score)
    return comparison


def _business_implications(
    metrics: dict[str, float],
    importance: pd.DataFrame,
) -> list[str]:
    """Translate measured behavior into bounded, non-causal business actions."""
    implications = [
        "Use scores to prioritize outreach, not as a standalone cancellation decision. "
        "The source is a historical cross-sectional snapshot, so associations are not causal.",
    ]
    if metrics["recall"] >= 0.70:
        implications.append(
            "The default threshold captures a substantial share of observed churners, "
            "which supports a broad proactive-retention queue."
        )
    else:
        implications.append(
            "The default threshold favors precision over coverage; test a lower operating "
            "threshold only with a defined retention-budget trade-off."
        )
    if metrics["precision"] >= 0.60:
        implications.append(
            "Positive predictions are concentrated enough to support a targeted offer test, "
            "provided campaign uplift is measured experimentally."
        )
    top_features = ", ".join(importance.head(3)["feature"].tolist())
    if top_features:
        implications.append(
            f"The strongest holdout permutation signals were {top_features}; investigate "
            "them as retention segments rather than causal levers."
        )
    return implications


def _format_report_markdown(report: dict[str, Any]) -> str:
    """Format an accessible Markdown model card from evaluation metadata."""
    protocol = report["evaluation_protocol"]
    lines = [
        "# Model Evaluation Report",
        "",
        f"**Selected model:** `{report['model_name']}`",
        "",
        "## Evaluation protocol",
        "",
        f"- **Population:** {protocol['population']}",
        f"- **Holdout:** {protocol['holdout']}",
        f"- **Selection:** {protocol['selection']}",
        f"- **Classification threshold:** {protocol['threshold']:.2f}",
        "",
        "## Final holdout metrics",
        "",
        "| Metric | Score |",
        "|---|---:|",
    ]
    for metric, value in report["holdout_metrics"].items():
        lines.append(f"| {metric.replace('_', ' ').title()} | {value:.4f} |")

    if report["candidate_comparison"]:
        lines.extend(
            [
                "",
                "## Candidate comparison (training CV)",
                "",
                "These values are from training folds only; the final holdout did not "
                "participate in model selection.",
                "",
                "| Model | Accuracy | Precision | Recall | F1 | ROC-AUC |",
                "|---|---:|---:|---:|---:|---:|",
            ]
        )
        for name, metrics in report["candidate_comparison"].items():
            lines.append(
                "| {name} | {accuracy:.4f} | {precision:.4f} | {recall:.4f} | "
                "{f1:.4f} | {roc_auc:.4f} |".format(
                    name=name,
                    accuracy=metrics.get("accuracy", 0.0),
                    precision=metrics.get("precision", 0.0),
                    recall=metrics.get("recall", 0.0),
                    f1=metrics.get("f1", 0.0),
                    roc_auc=metrics.get("roc_auc", 0.0),
                )
            )

    lines.extend(["", "## Top holdout permutation features", ""])
    for item in report["top_permutation_features"]:
        lines.append(f"- `{item['feature']}`: {item['importance_mean']:.4f} AUC decrease")

    lines.extend(["", "## Business implications", ""])
    lines.extend(f"- {item}" for item in report["business_implications"])
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- `reports/figures/roc_curve.png`",
            "- `reports/figures/precision_recall_curve.png`",
            "- `reports/figures/confusion_matrix.png`",
            "- `reports/figures/calibration_curve.png`",
            "- `reports/figures/feature_importance.png`",
            "- `reports/feature_importance.csv`",
        ]
    )
    return "\n".join(lines)
