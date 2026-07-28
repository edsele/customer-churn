"""Integration tests for the SQLite mart, SQL assets, and Tableau export."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.database import (
    execute_query,
    export_powerbi_dataset,
    export_tableau_dataset,
    initialize_database,
    run_sql_script,
)
from src.feature_engineering import engineer_features
from src.modeling import assign_risk_bands
from src.preprocessing import clean_data, load_raw_data


def _scored_fixture() -> pd.DataFrame:
    """Build a small feature-complete scored fixture from the checked-in raw data."""
    raw = load_raw_data()
    data = engineer_features(clean_data(raw.head(80)))
    data["churn_probability"] = [round(index / len(data), 4) for index in range(len(data))]
    data["predicted_churn_probability"] = data["churn_probability"]
    data["risk_band"] = assign_risk_bands(data["churn_probability"], threshold=0.5)
    data["is_high_risk"] = (data["churn_probability"] >= 0.5).astype(int)
    data["decision_threshold"] = 0.5
    data["revenue_at_risk"] = data["MonthlyCharges"] * data["churn_probability"]
    data["model_name"] = "test_model"
    data["model_version"] = "test"
    data["score_source"] = "test"
    return data


def test_database_views_and_sql_queries_execute(tmp_path: Path) -> None:
    database_path = tmp_path / "churn.db"
    data = _scored_fixture()
    initialize_database(data, database_path)

    view_rows = execute_query("SELECT COUNT(*) AS count FROM v_customer_analytics", database_path)
    assert int(view_rows.loc[0, "count"]) == len(data)
    prediction_schema = execute_query("PRAGMA table_info(customer_predictions)", database_path)
    primary_key = prediction_schema.loc[prediction_schema["name"] == "customerID", "pk"]
    assert int(primary_key.iloc[0]) == 1
    high_risk = execute_query("SELECT * FROM v_high_risk_customers", database_path)
    assert not high_risk.empty
    assert high_risk["risk_band"].eq("High").all()

    for script_path in sorted(Path("sql").glob("[0-9][0-9]_*.sql")):
        if script_path.name == "00_create_views.sql":
            continue
        result = run_sql_script(script_path, database_path)
        assert result is not None, script_path.name
        assert isinstance(result, pd.DataFrame)


def test_tableau_export_contains_documented_scoring_fields(tmp_path: Path) -> None:
    output_path = tmp_path / "tableau_export.csv"
    data = _scored_fixture()
    export_tableau_dataset(data, output_path)
    exported = pd.read_csv(output_path)
    required_columns = {
        "customerID",
        "Churn",
        "ChurnLabel",
        "AgeGroup",
        "predicted_churn_probability",
        "risk_band",
        "support_ticket_proxy",
        "revenue_at_risk",
    }
    assert required_columns.issubset(exported.columns)
    assert exported["predicted_churn_probability"].between(0, 1).all()


def test_powerbi_export_is_observed_only_and_contains_exposure_fields(tmp_path: Path) -> None:
    output_path = tmp_path / "powerbi_export.csv"
    data = _scored_fixture()
    scenario_copy = data.iloc[[0]].copy()
    scenario_copy["customerID"] = "SCENARIO-0001"
    scenario_copy["record_source"] = "synthetic_cohort"
    export_powerbi_dataset(pd.concat([data, scenario_copy], ignore_index=True), output_path)

    exported = pd.read_csv(output_path)
    assert len(exported) == len(data)
    assert set(exported["record_source"]) == {"observed"}
    assert {"high_risk_mrr_proxy", "retention_priority_value", "risk_band_order"}.issubset(
        exported.columns
    )
    assert (exported["high_risk_mrr_proxy"] >= 0).all()
