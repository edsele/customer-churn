"""Tests for portable dashboard-preview rendering and compatibility fallbacks."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from pathlib import Path

import pandas as pd

from src import dashboard_preview


def _preview_data() -> pd.DataFrame:
    """Return a compact, feature-complete observed/scenario preview fixture."""
    return pd.DataFrame(
        {
            "customerID": [f"CUSTOMER-{index}" for index in range(7)],
            "record_source": ["observed"] * 6 + ["synthetic_cohort"],
            "Churn": [0, 1, 0, 1, 0, 1, 1],
            "MonthlyCharges": [45.0, 65.0, 80.0, 95.0, 110.0, 125.0, 199.0],
            "lifetime_value_estimate": [3150.0, 4160.0, 3520.0, 2185.0, 1320.0, 7125.0, 13532.0],
            "churn_probability": [0.10, 0.80, 0.30, 0.65, 0.20, 0.90, 0.99],
            "Contract": [
                "Month-to-month",
                "One year",
                "Two year",
                "Month-to-month",
                "One year",
                "Two year",
                "Month-to-month",
            ],
            "InternetService": [
                "DSL",
                "Fiber optic",
                "No",
                "Fiber optic",
                "DSL",
                "No",
                "Fiber optic",
            ],
            "tenure_bucket": [
                "0-6 onboarding",
                "7-24 growth",
                "25-48 mature",
                "49+ loyal",
                "7-24 growth",
                "25-48 mature",
                "0-6 onboarding",
            ],
        }
    )


def test_generate_executive_summary_preview_renders_observed_snapshot(tmp_path: Path) -> None:
    """The preview should render from observed records with legacy score exports."""
    output_path = tmp_path / "executive_summary_preview.png"

    rendered_path = dashboard_preview.generate_executive_summary_preview(
        _preview_data(),
        output_path,
    )

    assert rendered_path == output_path
    assert output_path.is_file()
    assert output_path.stat().st_size > 1_000


def test_generate_preview_handles_missing_scores_at_the_default_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A score-less compatible export should still produce a transparent preview."""
    output_path = tmp_path / "default_preview.png"
    monkeypatch.setattr(dashboard_preview, "resolve_path", lambda _: output_path)

    rendered_path = dashboard_preview.generate_executive_summary_preview(
        _preview_data().drop(columns="churn_probability")
    )

    assert rendered_path == output_path
    assert output_path.is_file()
    assert output_path.stat().st_size > 1_000


def test_select_observed_snapshot_falls_back_for_missing_or_unusable_lineage() -> None:
    """Keep previews useful for legacy exports without observed rows."""
    data = _preview_data()
    config = {
        "data": {
            "record_source_column": "record_source",
            "observed_label": "observed",
        }
    }

    without_lineage, missing_scope = dashboard_preview._select_observed_snapshot(
        data.drop(columns="record_source"),
        config,
    )
    synthetic_only, synthetic_scope = dashboard_preview._select_observed_snapshot(
        data.loc[data["record_source"].eq("synthetic_cohort")],
        config,
    )
    non_mapping, non_mapping_scope = dashboard_preview._select_observed_snapshot(
        data,
        {"data": "legacy configuration"},
    )

    assert without_lineage.equals(data.drop(columns="record_source"))
    assert missing_scope == "all supplied records (n=7)"
    assert synthetic_only.equals(data.loc[data["record_source"].eq("synthetic_cohort")])
    assert synthetic_scope == "all supplied records (n=1)"
    assert non_mapping.equals(data)
    assert non_mapping_scope == "all supplied records (n=7)"


def test_risk_summary_uses_displayed_probabilities_when_raw_fields_are_absent() -> None:
    """Legacy exports retain their threshold and weighted-MRR fallback behavior."""
    data = pd.DataFrame({"MonthlyCharges": [100.0, 200.0]})
    probabilities = pd.Series([0.49, 0.51])

    high_risk, revenue_at_risk = dashboard_preview._risk_summary(data, probabilities, threshold=0.5)

    assert high_risk == 1
    assert revenue_at_risk == 151.0


def test_risk_summary_accepts_raw_export_fields_with_missing_values() -> None:
    """Raw-score fields remain authoritative even when a CSV contains bad cells."""
    data = pd.DataFrame(
        {
            "MonthlyCharges": [100.0, 200.0],
            "is_high_risk": ["1", "not-a-number"],
            "revenue_at_risk": ["99.49", "not-a-number"],
        }
    )

    high_risk, revenue_at_risk = dashboard_preview._risk_summary(
        data,
        pd.Series([0.0, 1.0]),
        threshold=0.5,
    )

    assert high_risk == 1
    assert revenue_at_risk == 99.49
