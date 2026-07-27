"""SQLite data-mart operations for churn analysis and Tableau exports."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import load_config, resolve_path

logger = logging.getLogger(__name__)

CUSTOMERS_TABLE = "customers"
PREDICTIONS_TABLE = "customer_predictions"
VIEW_NAMES = [
    "v_high_risk_customers",
    "v_retention_snapshot",
    "v_customer_segments",
    "v_customer_analytics",
]
PREDICTION_COLUMNS = [
    "customerID",
    "source_customer_id",
    "model_name",
    "model_version",
    "churn_probability",
    "risk_band",
    "is_high_risk",
    "decision_threshold",
    "revenue_at_risk",
    "score_source",
]


def get_engine(db_path: Path | None = None) -> Engine:
    """Create a SQLAlchemy engine for the project-local SQLite data mart."""
    config = load_config()
    path = db_path or resolve_path(config["paths"]["database"])
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path.as_posix()}")


def load_dataframe_to_db(
    df: pd.DataFrame,
    db_path: Path | None = None,
    table_name: str = CUSTOMERS_TABLE,
    if_exists: str = "replace",
) -> None:
    """Persist a DataFrame to SQLite with a clear row-count audit message."""
    engine = get_engine(db_path)
    df.to_sql(table_name, engine, if_exists=if_exists, index=False)
    logger.info("Loaded %d rows into SQLite table '%s'.", len(df), table_name)


def build_prediction_table(scored_customers: pd.DataFrame) -> pd.DataFrame:
    """Extract a stable score-table contract from scored or unscored customers."""
    predictions = pd.DataFrame(index=scored_customers.index)
    for column in PREDICTION_COLUMNS:
        if column in scored_customers.columns:
            predictions[column] = scored_customers[column]
        elif column in {"customerID", "source_customer_id"}:
            predictions[column] = scored_customers.get(column, pd.NA)
        else:
            predictions[column] = pd.NA
    return predictions[PREDICTION_COLUMNS]


def execute_query(query: str, db_path: Path | None = None) -> pd.DataFrame:
    """Run one read query and return the result as a DataFrame."""
    engine = get_engine(db_path)
    with engine.connect() as connection:
        return pd.read_sql(text(query), connection)


def run_sql_script(script_path: Path, db_path: Path | None = None) -> pd.DataFrame | None:
    """Execute a SQL asset, returning a table when its first statement is a query."""
    sql = script_path.read_text(encoding="utf-8")
    executable = _strip_sql_comments(sql).strip()
    if executable.upper().startswith(("SELECT", "WITH", "EXPLAIN")):
        return execute_query(sql, db_path)

    engine = get_engine(db_path)
    with engine.begin() as connection:
        for statement in _split_statements(sql):
            if _strip_sql_comments(statement).strip():
                connection.execute(text(statement))
    logger.info("Executed SQL script: %s", script_path.name)
    return None


def _strip_sql_comments(sql: str) -> str:
    """Remove full-line SQL comments for lightweight statement classification."""
    return "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))


def _split_statements(sql: str) -> list[str]:
    """Split the project's simple, semicolon-terminated SQL assets."""
    uncommented_sql = _strip_sql_comments(sql)
    return [statement.strip() for statement in uncommented_sql.split(";") if statement.strip()]


def initialize_database(
    scored_customers: pd.DataFrame,
    db_path: Path | None = None,
) -> Engine:
    """Materialize customer and prediction tables, indexes, and reporting views."""
    if (
        scored_customers["customerID"].isna().any()
        or scored_customers["customerID"].duplicated().any()
    ):
        raise ValueError(
            "The SQLite customer table requires one non-null, unique customerID per row."
        )

    engine = get_engine(db_path)
    with engine.begin() as connection:
        for view_name in VIEW_NAMES:
            connection.execute(text(f"DROP VIEW IF EXISTS {view_name}"))
        connection.execute(text(f"DROP TABLE IF EXISTS {PREDICTIONS_TABLE}"))

    scored_customers.to_sql(CUSTOMERS_TABLE, engine, if_exists="replace", index=False)

    views_script = resolve_path("sql/00_create_views.sql")
    if not views_script.exists():
        raise FileNotFoundError(f"Required SQL view script not found: {views_script}")
    run_sql_script(views_script, db_path)

    predictions = build_prediction_table(scored_customers)
    predictions.to_sql(PREDICTIONS_TABLE, engine, if_exists="append", index=False)
    logger.info(
        "Initialized SQLite data mart with %d customers and %d prediction rows.",
        len(scored_customers),
        len(predictions),
    )
    return engine


def export_tableau_dataset(
    scored_customers: pd.DataFrame,
    output_path: Path | None = None,
) -> Path:
    """Export a scored, Tableau-ready customer snapshot with readable labels."""
    config = load_config()
    path = output_path or resolve_path(config["paths"]["tableau_export"])
    path.parent.mkdir(parents=True, exist_ok=True)
    export = scored_customers.copy()

    if "Churn" in export.columns:
        export["ChurnLabel"] = export["Churn"].map({1: "Yes", 0: "No"}).fillna("Unknown")
    export["AgeGroup"] = (
        export["SeniorCitizen"].map({1: "Senior (65+)", 0: "Non-Senior"}).fillna("Unknown")
    )
    export["predicted_churn_probability"] = export.get(
        "churn_probability",
        pd.Series(np.nan, index=export.index),
    )
    export["HighRiskFlag"] = (
        export.get(
            "is_high_risk",
            pd.Series(0, index=export.index),
        )
        .fillna(0)
        .astype(int)
    )
    export["revenue_at_risk"] = export.get(
        "revenue_at_risk",
        export["MonthlyCharges"] * export["predicted_churn_probability"],
    )
    export.to_csv(path, index=False)
    logger.info("Exported Tableau dataset with %d rows to %s", len(export), path)
    return path
