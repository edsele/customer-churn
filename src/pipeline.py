"""Command-line orchestration for the reproducible churn analytics workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from src.config import load_config, resolve_path, setup_logging
from src.dashboard_preview import generate_executive_summary_preview
from src.database import export_powerbi_dataset, export_tableau_dataset, initialize_database
from src.eda import run_eda
from src.evaluation import generate_evaluation_report
from src.feature_engineering import run_feature_engineering
from src.modeling import (
    save_models,
    score_analytics_scenario,
    select_best_model,
    train_models,
)
from src.preprocessing import run_preprocessing_pipeline

logger = logging.getLogger(__name__)


def run_full_pipeline(skip_training: bool = False) -> dict[str, Any]:
    """Run cleaning, scenario creation, analysis, model validation, and exports."""
    config = load_config()
    logger.info("Starting %s v%s", config["project"]["name"], config["project"]["version"])

    scenario, validation = run_preprocessing_pipeline(export=True)
    featured = run_feature_engineering(scenario, export=True)
    summary: dict[str, Any] = {
        "project_version": config["project"]["version"],
        "observed_records": int(
            (
                featured[config["data"]["record_source_column"]] == config["data"]["observed_label"]
            ).sum()
        ),
        "analytics_scenario_records": len(featured),
        "validation_passed": validation.passed,
        "observed_churn_rate": validation.observed_churn_rate,
        "scenario_churn_rate": validation.scenario_churn_rate,
    }

    if skip_training:
        run_eda(featured)
        summary["training"] = "skipped"
        summary["scored_artifacts"] = "preserved; run the full pipeline to refresh them"
        _write_run_manifest(summary, resolve_path("reports/smoke_run_manifest.json"))
        logger.info(
            "Pipeline smoke run completed without model training; scored database and dashboard "
            "artifacts were preserved."
        )
        return summary

    results, split = train_models(featured)
    best_model = select_best_model(results)
    save_models(results)
    evaluation = generate_evaluation_report(
        best_model.pipeline,
        split.X_test,
        split.y_test,
        best_model.name,
        candidate_results=results,
        training_cv=best_model.cv_metrics,
    )
    scored = score_analytics_scenario(featured, best_model.pipeline, best_model.name)
    scored_path = resolve_path(config["paths"]["scored_data"])
    scored_path.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(scored_path, index=False)

    initialize_database(scored)
    export_tableau_dataset(scored)
    powerbi_export_path = export_powerbi_dataset(scored)
    run_eda(scored)
    preview_path = generate_executive_summary_preview(scored)

    summary.update(
        {
            "selected_model": best_model.name,
            "selection_cv_roc_auc": best_model.selection_score,
            "holdout_metrics": evaluation["holdout_metrics"],
            "dashboard_preview": str(preview_path.relative_to(resolve_path("."))),
            "powerbi_export": str(powerbi_export_path.relative_to(resolve_path("."))),
        }
    )
    _write_run_manifest(summary)
    logger.info(
        "Pipeline complete. Selected %s with holdout ROC-AUC %.3f.",
        best_model.name,
        evaluation["holdout_metrics"]["roc_auc"],
    )
    return summary


def _write_run_manifest(summary: dict[str, Any], output_path: Path | None = None) -> None:
    """Persist a traceable machine-readable record of the current pipeline run."""
    output_path = output_path or resolve_path("reports/run_manifest.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**summary, "run_context": _build_run_context()}
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Run manifest saved to %s", output_path)


def _build_run_context() -> dict[str, Any]:
    """Capture code, input, and environment details needed to reproduce a run."""
    config = load_config()
    raw_path = resolve_path(config["paths"]["raw_data"])
    config_path = resolve_path("config/config.yaml")
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "git_revision": _git_revision(),
        "git_dirty": _git_is_dirty(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "raw_data_sha256": _sha256_file(raw_path),
        "config_sha256": _sha256_file(config_path),
        "package_versions": _package_versions(),
    }


def _sha256_file(path: Path) -> str | None:
    """Return a file checksum when the input exists, otherwise ``None``."""
    if not path.exists():
        return None

    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_versions() -> dict[str, str | None]:
    """Record versions for libraries that affect pipeline behavior or output."""
    packages = [
        "joblib",
        "matplotlib",
        "numpy",
        "pandas",
        "PyYAML",
        "scikit-learn",
        "seaborn",
        "SQLAlchemy",
    ]
    versions: dict[str, str | None] = {}
    for package in packages:
        try:
            versions[package] = version(package)
        except PackageNotFoundError:
            versions[package] = None
    return versions


def _git_revision() -> str | None:
    """Return the checked-out revision without making Git availability a requirement."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=resolve_path("."),
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def _git_is_dirty() -> bool | None:
    """Return whether tracked or untracked files differed when the run was recorded."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=resolve_path("."),
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return bool(result.stdout.strip())


def main(argv: list[str] | None = None) -> int:
    """Parse CLI options and execute the pipeline."""
    parser = argparse.ArgumentParser(
        description="Build the customer churn analytics data mart and model artifacts."
    )
    parser.add_argument(
        "--skip-training",
        action="store_true",
        help="Run validation and EDA without changing scored model, SQL, or dashboard artifacts.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Minimum log level written to standard output.",
    )
    arguments = parser.parse_args(argv)
    setup_logging(arguments.log_level)
    run_full_pipeline(skip_training=arguments.skip_training)
    return 0


if __name__ == "__main__":
    sys.exit(main())
