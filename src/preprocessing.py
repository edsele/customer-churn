"""Validated loading, cleaning, and scenario construction for customer churn data.

The raw IBM Telco file contains 7,043 observed customer snapshots.  The optional
analytics scenario expands those snapshots to 21,000 rows for dashboard and EDA
demonstrations.  Scenario rows are explicitly labeled and are never treated as
independent evidence in the default model evaluation.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.config import load_config, resolve_path

logger = logging.getLogger(__name__)


@dataclass
class ValidationReport:
    """Portable summary of raw-data quality checks and pipeline outputs."""

    input_rows: int
    duplicate_ids: int = 0
    missing_values: dict[str, int] = field(default_factory=dict)
    range_violations: dict[str, int] = field(default_factory=dict)
    coercion_failures: dict[str, int] = field(default_factory=dict)
    invalid_churn_values: int = 0
    missing_columns: list[str] = field(default_factory=list)
    passed: bool = True
    messages: list[str] = field(default_factory=list)
    output_rows: int | None = None
    scenario_rows: int | None = None
    observed_churn_rate: float | None = None
    scenario_churn_rate: float | None = None
    scenario_churn_rate_delta: float | None = None

    @property
    def row_count(self) -> int:
        """Backwards-compatible alias for the number of source rows."""
        return self.input_rows

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable validation metadata."""
        return asdict(self)


def load_raw_data(path: Path | None = None) -> pd.DataFrame:
    """Load the raw IBM Telco customer snapshot without mutating it."""
    config = load_config()
    file_path = path or resolve_path(config["paths"]["raw_data"])
    logger.info("Loading raw data from %s", file_path)
    if not file_path.exists():
        raise FileNotFoundError(
            f"Raw data was not found at {file_path}. See data/README.md for setup."
        )
    data = pd.read_csv(file_path, dtype={"customerID": "string"})
    data.columns = data.columns.str.strip()
    return data


def validate_data(df: pd.DataFrame) -> ValidationReport:
    """Validate required columns, identifiers, target values, and numeric ranges."""
    config = load_config()
    validation_config = config["validation"]
    id_col = config["data"]["id_column"]
    churn_col = config["data"]["churn_column"]
    report = ValidationReport(input_rows=len(df))

    report.missing_columns = [
        column
        for column in validation_config["required_columns"]
        if column not in df.columns
    ]
    if report.missing_columns:
        report.passed = False
        report.messages.append(f"Missing required columns: {report.missing_columns}")
        return report

    report.duplicate_ids = int(df[id_col].astype("string").duplicated().sum())
    if report.duplicate_ids:
        report.messages.append(f"Found {report.duplicate_ids} duplicate customer IDs.")

    report.missing_values = {
        column: int(df[column].isna().sum())
        for column in df.columns
        if int(df[column].isna().sum()) > 0
    }

    for column, (minimum, maximum) in validation_config["numeric_ranges"].items():
        raw_values = df[column].replace(r"^\s*$", np.nan, regex=True)
        numeric_values = pd.to_numeric(raw_values, errors="coerce")
        failed_coercion = raw_values.notna() & numeric_values.isna()
        if failed_coercion.any():
            report.coercion_failures[column] = int(failed_coercion.sum())
        violations = numeric_values.notna() & (
            (numeric_values < minimum) | (numeric_values > maximum)
        )
        if violations.any():
            report.range_violations[column] = int(violations.sum())

    allowed_churn = set(validation_config["allowed_churn_values"])
    invalid_churn = ~df[churn_col].isin(allowed_churn)
    report.invalid_churn_values = int(invalid_churn.sum())

    if report.range_violations:
        report.passed = False
        report.messages.append("Numeric range violations detected.")
    if report.invalid_churn_values:
        report.passed = False
        report.messages.append("Invalid churn labels detected.")

    logger.info("Raw validation report: %s", report.to_dict())
    return report


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Standardize types, remove duplicate IDs, and impute defensible values."""
    config = load_config()
    id_col = config["data"]["id_column"]
    churn_col = config["data"]["churn_column"]
    source_col = config["data"]["source_id_column"]
    record_source_col = config["data"]["record_source_column"]

    cleaned = df.copy()
    cleaned.columns = cleaned.columns.str.strip()
    cleaned = cleaned.replace(r"^\s*$", np.nan, regex=True)
    cleaned[id_col] = cleaned[id_col].astype("string").str.strip()
    cleaned = cleaned.drop_duplicates(subset=[id_col], keep="first").copy()

    for column in ("tenure", "MonthlyCharges", "TotalCharges"):
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    tenure_median = int(cleaned["tenure"].median())
    monthly_charge_median = float(cleaned["MonthlyCharges"].median())
    cleaned["tenure"] = cleaned["tenure"].fillna(tenure_median).round().astype(int)
    cleaned["MonthlyCharges"] = cleaned["MonthlyCharges"].fillna(monthly_charge_median)
    cleaned["TotalCharges"] = cleaned["TotalCharges"].fillna(
        cleaned["MonthlyCharges"] * cleaned["tenure"]
    )
    cleaned["TotalCharges"] = cleaned["TotalCharges"].round(2)

    categorical_columns = cleaned.select_dtypes(include=["object", "string"]).columns
    for column in categorical_columns:
        if column not in {id_col, churn_col}:
            cleaned[column] = cleaned[column].fillna("Unknown")

    churn_mapping = {"Yes": 1, "No": 0}
    mapped_churn = cleaned[churn_col].map(churn_mapping)
    if mapped_churn.isna().any():
        invalid_values = sorted(cleaned.loc[mapped_churn.isna(), churn_col].unique())
        raise ValueError(f"Cannot clean invalid churn values: {invalid_values}")
    cleaned[churn_col] = mapped_churn.astype(int)
    cleaned[source_col] = cleaned[id_col].astype("string")
    cleaned[record_source_col] = config["data"]["observed_label"]

    if cleaned.isna().any().any():
        remaining = cleaned.columns[cleaned.isna().any()].tolist()
        raise ValueError(f"Cleaning left missing values in columns: {remaining}")

    logger.info("Cleaned observed dataset: %d rows, %d columns", *cleaned.shape)
    return cleaned


def augment_dataset(
    df: pd.DataFrame,
    target_records: int | None = None,
    random_seed: int | None = None,
) -> pd.DataFrame:
    """Create a labeled, class-proportionate analytics scenario.

    The method samples within the observed churn classes so scenario prevalence
    matches the source population.  It applies only small numeric perturbations
    to copied profiles and never references the churn target while perturbing
    features.  `source_customer_id` makes every synthetic lineage auditable.
    """
    config = load_config()
    data_config = config["data"]
    target = target_records or data_config["target_records"]
    seed = config["project"]["random_seed"] if random_seed is None else random_seed
    id_col = data_config["id_column"]
    churn_col = data_config["churn_column"]
    source_col = data_config["source_id_column"]
    record_source_col = data_config["record_source_column"]

    if target < len(df):
        raise ValueError("target_records cannot be smaller than the observed dataset.")

    observed = df.copy()
    observed[source_col] = observed.get(source_col, observed[id_col]).astype(str)
    observed[record_source_col] = data_config["observed_label"]
    if len(observed) == target:
        return observed.reset_index(drop=True)

    rng = np.random.default_rng(seed)
    desired_counts = _allocate_target_class_counts(observed[churn_col], target)
    extras: list[pd.DataFrame] = []
    next_index = 1

    for label, target_count in desired_counts.items():
        subgroup = observed.loc[observed[churn_col] == label]
        additional_count = target_count - len(subgroup)
        if additional_count <= 0:
            continue
        sample_indices = rng.choice(subgroup.index.to_numpy(), size=additional_count)
        extra = subgroup.loc[sample_indices].copy().reset_index(drop=True)
        extra[id_col] = [
            _generate_scenario_customer_id(next_index + offset, rng)
            for offset in range(additional_count)
        ]
        next_index += additional_count
        extra[record_source_col] = data_config["synthetic_label"]
        extras.append(_perturb_synthetic_profiles(extra, rng))

    scenario = pd.concat([observed, *extras], ignore_index=True)
    if scenario[id_col].duplicated().any():
        raise RuntimeError("Scenario construction produced duplicate customer IDs.")

    logger.info(
        "Built analytics scenario with %d rows (%d observed, %d synthetic).",
        len(scenario),
        (scenario[record_source_col] == data_config["observed_label"]).sum(),
        (scenario[record_source_col] == data_config["synthetic_label"]).sum(),
    )
    return scenario.reset_index(drop=True)


def _allocate_target_class_counts(labels: pd.Series, target: int) -> dict[int, int]:
    """Allocate target rows by observed class prevalence with exact total size."""
    counts = labels.value_counts().sort_index()
    proportions = counts / counts.sum()
    raw_targets = proportions * target
    allocated = raw_targets.astype(int)
    remainder = target - int(allocated.sum())
    for label in (raw_targets - allocated).sort_values(ascending=False).index[:remainder]:
        allocated.loc[label] += 1
    return {int(label): int(count) for label, count in allocated.items()}


def _perturb_synthetic_profiles(
    profiles: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """Apply bounded, target-independent jitter while preserving charge logic."""
    config = load_config()
    jitter_config = config["augmentation"]
    synthetic = profiles.copy()
    original_tenure = synthetic["tenure"].clip(lower=1).astype(float)
    original_monthly = synthetic["MonthlyCharges"].astype(float)
    charge_ratio = synthetic["TotalCharges"].astype(float) / (
        original_tenure * original_monthly.clip(lower=1)
    )
    charge_ratio = charge_ratio.replace([np.inf, -np.inf], np.nan).fillna(1.0)
    charge_ratio = charge_ratio.clip(lower=0.5, upper=1.5)

    tenure_noise = rng.integers(
        -jitter_config["max_tenure_jitter_months"],
        jitter_config["max_tenure_jitter_months"] + 1,
        size=len(synthetic),
    )
    synthetic["tenure"] = np.clip(
        synthetic["tenure"].astype(int) + tenure_noise,
        0,
        72,
    ).astype(int)
    monthly_noise = rng.uniform(
        -jitter_config["monthly_charge_jitter_pct"],
        jitter_config["monthly_charge_jitter_pct"],
        size=len(synthetic),
    )
    synthetic["MonthlyCharges"] = np.clip(
        original_monthly * (1 + monthly_noise),
        0,
        200,
    ).round(2)
    synthetic["TotalCharges"] = (
        synthetic["MonthlyCharges"]
        * synthetic["tenure"]
        * charge_ratio.to_numpy()
    ).clip(lower=0, upper=10000).round(2)
    return synthetic


def _generate_scenario_customer_id(index: int, rng: np.random.Generator) -> str:
    """Generate a unique, clearly synthetic customer identifier."""
    suffix = "".join(rng.choice(list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"), size=4))
    return f"SCN-{index:05d}-{suffix}"


def assess_scenario_distribution(
    observed: pd.DataFrame,
    scenario: pd.DataFrame,
) -> dict[str, float]:
    """Return compact distribution checks for the generated scenario."""
    config = load_config()
    churn_col = config["data"]["churn_column"]
    observed_rate = float(observed[churn_col].mean())
    scenario_rate = float(scenario[churn_col].mean())
    checks = {
        "observed_churn_rate": observed_rate,
        "scenario_churn_rate": scenario_rate,
        "churn_rate_delta": scenario_rate - observed_rate,
        "tenure_mean_delta": float(scenario["tenure"].mean() - observed["tenure"].mean()),
        "monthly_charge_mean_delta": float(
            scenario["MonthlyCharges"].mean() - observed["MonthlyCharges"].mean()
        ),
    }
    return checks


def export_cleaned_data(df: pd.DataFrame, output_path: Path | None = None) -> Path:
    """Persist observed, cleaned customer data to a project-relative CSV."""
    config = load_config()
    path = output_path or resolve_path(config["paths"]["processed_data"])
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Exported cleaned data to %s", path)
    return path


def export_scenario_data(df: pd.DataFrame, output_path: Path | None = None) -> Path:
    """Persist the explicitly labeled analytics scenario to CSV."""
    config = load_config()
    path = output_path or resolve_path(config["paths"]["scenario_data"])
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logger.info("Exported analytics scenario to %s", path)
    return path


def write_validation_report(report: ValidationReport, path: Path | None = None) -> Path:
    """Write a machine-readable audit report for the preprocessing run."""
    config = load_config()
    output_path = path or resolve_path(config["paths"]["validation_report"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8"
    )
    logger.info("Wrote data quality report to %s", output_path)
    return output_path


def run_preprocessing_pipeline(
    raw_path: Path | None = None,
    export: bool = True,
    augment: bool | None = None,
) -> tuple[pd.DataFrame, ValidationReport]:
    """Load, validate, clean, and optionally expand a dashboard/EDA scenario."""
    config = load_config()
    raw = load_raw_data(raw_path)
    report = validate_data(raw)
    if not report.passed:
        raise ValueError(f"Raw data validation failed: {report.messages}")

    cleaned = clean_data(raw)
    should_augment = config["augmentation"]["enabled"] if augment is None else augment
    scenario = (
        augment_dataset(cleaned)
        if should_augment
        else cleaned.copy().reset_index(drop=True)
    )
    distribution = assess_scenario_distribution(cleaned, scenario)
    report.output_rows = len(cleaned)
    report.scenario_rows = len(scenario)
    report.observed_churn_rate = distribution["observed_churn_rate"]
    report.scenario_churn_rate = distribution["scenario_churn_rate"]
    report.scenario_churn_rate_delta = distribution["churn_rate_delta"]

    if export:
        export_cleaned_data(cleaned)
        export_scenario_data(scenario)
        write_validation_report(report)

    return scenario, report
