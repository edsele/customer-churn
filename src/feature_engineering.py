"""Feature engineering and model-ready transformations for churn analytics."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.config import load_config, resolve_path

logger = logging.getLogger(__name__)

FEATURE_DOCUMENTATION: dict[str, dict[str, str]] = {
    "tenure_bucket": {
        "description": "Lifecycle stage derived from tenure in months.",
        "usage": "Model and dashboard",
    },
    "revenue_per_month": {
        "description": "Realized charges divided by tenure; uses MonthlyCharges for new customers.",
        "usage": "Model and dashboard",
    },
    "service_count": {
        "description": "Count of active connectivity, protection, support, and streaming services.",
        "usage": "Model and dashboard",
    },
    "avg_services_purchased": {
        "description": "Compatibility label for the per-customer active service count.",
        "usage": "Dashboard only",
    },
    "contract_risk_score": {
        "description": (
            "Business-rule score for contract flexibility; 3 is month-to-month, 1 is two-year."
        ),
        "usage": "Dashboard only; raw Contract is modelled categorically",
    },
    "customer_engagement_score": {
        "description": (
            "Explainable composite of adopted services, security add-ons, tenure, "
            "and contract depth."
        ),
        "usage": "Model and dashboard",
    },
    "monthly_charge_ratio": {
        "description": "Monthly charge relative to the scenario median; descriptive only.",
        "usage": "Dashboard only",
    },
    "lifetime_value_estimate": {
        "description": (
            "Remaining-revenue proxy: MonthlyCharges multiplied by max(72 - tenure, 0)."
        ),
        "usage": "Dashboard only",
    },
    "payment_risk_flag": {
        "description": "Electronic-check indicator used as a descriptive operational signal.",
        "usage": "Model and dashboard",
    },
    "senior_household_flag": {
        "description": "Senior customer without partner or dependents.",
        "usage": "Model and dashboard",
    },
    "internet_fiber_flag": {
        "description": "Fiber-optic service indicator for dashboard segmentation.",
        "usage": "Dashboard only; raw InternetService is modelled categorically",
    },
    "support_ticket_proxy": {
        "description": (
            "Estimated support need from service setup and tenure, not an observed ticket count."
        ),
        "usage": "Dashboard only",
    },
    "support_intensity": {
        "description": (
            "Estimated support need normalized by tenure, with new customers "
            "protected from division by zero."
        ),
        "usage": "Dashboard only",
    },
}

SERVICE_COLUMNS = [
    "PhoneService",
    "MultipleLines",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
]

CONTRACT_RISK = {
    "Month-to-month": 3,
    "One year": 2,
    "Two year": 1,
}


def create_tenure_bucket(tenure: int | float) -> str:
    """Map tenure to a stable, business-readable lifecycle segment."""
    if tenure <= 6:
        return "0-6 onboarding"
    if tenure <= 24:
        return "7-24 growth"
    if tenure <= 48:
        return "25-48 mature"
    return "49+ loyal"


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create documented, scoring-time-safe features from a customer snapshot.

    No engineered feature references the churn label.  The churn column is only
    converted to binary when a raw input still carries Yes/No labels.
    """
    config = load_config()
    churn_col = config["data"]["churn_column"]
    enriched = df.copy()

    if churn_col in enriched and enriched[churn_col].dtype == object:
        enriched[churn_col] = enriched[churn_col].map({"Yes": 1, "No": 0})

    enriched["tenure_bucket"] = enriched["tenure"].apply(create_tenure_bucket)
    tenure_denominator = enriched["tenure"].replace(0, np.nan)
    enriched["revenue_per_month"] = (
        (enriched["TotalCharges"] / tenure_denominator).fillna(enriched["MonthlyCharges"]).round(2)
    )
    enriched["service_count"] = enriched.apply(_count_active_services, axis=1)
    enriched["avg_services_purchased"] = enriched["service_count"]
    enriched["contract_risk_score"] = enriched["Contract"].map(CONTRACT_RISK).fillna(2).astype(int)
    enriched["customer_engagement_score"] = enriched.apply(_engagement_score, axis=1)
    median_charge = float(enriched["MonthlyCharges"].median())
    enriched["monthly_charge_ratio"] = (enriched["MonthlyCharges"] / max(median_charge, 1.0)).round(
        3
    )
    enriched["lifetime_value_estimate"] = (
        enriched["MonthlyCharges"] * (72 - enriched["tenure"]).clip(lower=0, upper=72)
    ).round(2)
    enriched["payment_risk_flag"] = (enriched["PaymentMethod"] == "Electronic check").astype(int)
    enriched["senior_household_flag"] = (
        (enriched["SeniorCitizen"] == 1)
        & (enriched["Partner"] == "No")
        & (enriched["Dependents"] == "No")
    ).astype(int)
    enriched["internet_fiber_flag"] = (enriched["InternetService"] == "Fiber optic").astype(int)
    enriched["support_ticket_proxy"] = enriched.apply(
        _estimate_support_ticket_proxy,
        axis=1,
    )
    enriched["support_intensity"] = (
        enriched["support_ticket_proxy"] / enriched["tenure"].replace(0, 1)
    ).round(3)

    logger.info("Engineered %d documented features.", len(FEATURE_DOCUMENTATION))
    return enriched


def _count_active_services(row: pd.Series) -> int:
    """Count active subscriptions without counting 'No ... service' labels."""
    count = sum(str(row.get(column, "No")) == "Yes" for column in SERVICE_COLUMNS)
    has_internet = row.get("InternetService") not in {"No", "No internet service", None}
    return int(count + has_internet)


def _engagement_score(row: pd.Series) -> float:
    """Calculate an explainable engagement score without using the target label."""
    services = _count_active_services(row)
    security_adoption = int(row.get("OnlineSecurity") == "Yes")
    backup_adoption = int(row.get("OnlineBackup") == "Yes")
    tenure_component = min(float(row.get("tenure", 0)) / 72.0, 1.0) * 5
    contract_component = {"Two year": 2, "One year": 1}.get(row.get("Contract"), 0)
    return round(
        services * 1.5
        + security_adoption * 2
        + backup_adoption
        + tenure_component
        + contract_component,
        2,
    )


def _estimate_support_ticket_proxy(row: pd.Series) -> int:
    """Estimate support need from observable service complexity only.

    This is a transparent proxy because the source does not include support
    interactions.  It deliberately does not read `Churn` or any post-churn
    field, so it cannot leak the target into the model.
    """
    score = 0
    has_internet = row.get("InternetService") != "No"
    score += int(row.get("InternetService") == "Fiber optic")
    score += int(has_internet and row.get("TechSupport") != "Yes")
    score += int(has_internet and row.get("OnlineSecurity") == "No")
    score += int(has_internet and row.get("DeviceProtection") == "No")
    score += int(row.get("Contract") == "Month-to-month")
    score += int(float(row.get("tenure", 0)) <= 6)
    return int(min(score, 6))


def get_feature_columns() -> tuple[list[str], list[str]]:
    """Return model inputs known at scoring time, split by transform type."""
    numeric = [
        "SeniorCitizen",
        "tenure",
        "MonthlyCharges",
        "TotalCharges",
        "revenue_per_month",
        "service_count",
        "customer_engagement_score",
        "payment_risk_flag",
        "senior_household_flag",
    ]
    categorical = [
        "gender",
        "Partner",
        "Dependents",
        "PhoneService",
        "MultipleLines",
        "InternetService",
        "OnlineSecurity",
        "OnlineBackup",
        "DeviceProtection",
        "TechSupport",
        "StreamingTV",
        "StreamingMovies",
        "Contract",
        "PaperlessBilling",
        "PaymentMethod",
        "tenure_bucket",
    ]
    return numeric, categorical


def build_preprocessor() -> ColumnTransformer:
    """Build a fold-safe preprocessing transformer for all model inputs."""
    numeric, categorical = get_feature_columns()
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric),
            ("categorical", categorical_pipeline, categorical),
        ],
        remainder="drop",
    )


def export_feature_documentation(output_path: Path | None = None) -> Path:
    """Write feature definitions, provenance, and intended use to Markdown."""
    path = output_path or resolve_path("reports/feature_engineering.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Feature Engineering Documentation",
        "",
        "All features are calculated from attributes available in the customer snapshot.",
        "The churn label is never used to create a feature.",
        "",
        "| Feature | Description | Intended use |",
        "|---|---|---|",
    ]
    for name, metadata in FEATURE_DOCUMENTATION.items():
        lines.append(f"| `{name}` | {metadata['description']} | {metadata['usage']} |")
    lines.extend(
        [
            "",
            "## Modeling boundary",
            "",
            "`contract_risk_score`, `internet_fiber_flag`, `monthly_charge_ratio`, and "
            "`lifetime_value_estimate` are retained for business reporting but are not "
            "model features where they duplicate raw fields or depend on a scenario-wide "
            "statistic. The model uses a fold-safe preprocessing pipeline.",
            "",
            "## Support-ticket proxy",
            "",
            "The IBM source does not include support ticket counts. `support_ticket_proxy` "
            "is an estimated support-need indicator based on observable service setup and "
            "tenure. It is dashboard-only, not an observed operational metric or model "
            "input, and should be replaced with actual CRM/support data in production.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Feature documentation exported to %s", path)
    return path


def run_feature_engineering(df: pd.DataFrame, export: bool = True) -> pd.DataFrame:
    """Engineer features and optionally persist the enriched analytics scenario."""
    featured = engineer_features(df)
    if export:
        config = load_config()
        path = resolve_path(config["paths"]["features_data"])
        path.parent.mkdir(parents=True, exist_ok=True)
        featured.to_csv(path, index=False)
        export_feature_documentation()
    return featured


def get_feature_documentation() -> dict[str, dict[str, str]]:
    """Return a defensive copy of feature documentation metadata."""
    return {name: details.copy() for name, details in FEATURE_DOCUMENTATION.items()}
