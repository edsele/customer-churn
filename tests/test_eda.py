"""Tests for repeatable EDA loading, rendering, and observed-source reporting."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

from pathlib import Path

import pandas as pd
import pytest

from src import eda


def _eda_data() -> pd.DataFrame:
    """Return a small feature-complete fixture with one scenario descendant."""
    return pd.DataFrame(
        {
            "customerID": [f"CUSTOMER-{index}" for index in range(7)],
            "record_source": ["observed"] * 6 + ["synthetic_cohort"],
            "Churn": [0, 1, 0, 1, 0, 1, 1],
            "tenure": [2, 8, 28, 49, 12, 36, 4],
            "MonthlyCharges": [45.0, 65.0, 80.0, 95.0, 110.0, 125.0, 199.0],
            "TotalCharges": [90.0, 520.0, 2240.0, 4655.0, 1320.0, 4500.0, 796.0],
            "revenue_per_month": [45.0, 65.0, 80.0, 95.0, 110.0, 125.0, 199.0],
            "service_count": [2, 3, 4, 5, 3, 4, 6],
            "support_ticket_proxy": [3, 4, 2, 1, 3, 2, 6],
            "customer_engagement_score": [2.0, 4.0, 5.0, 7.0, 4.5, 6.0, 1.5],
            "support_intensity": [1.5, 0.5, 0.1, 0.0, 0.2, 0.1, 1.5],
            "Contract": [
                "Month-to-month",
                "One year",
                "Two year",
                "Month-to-month",
                "One year",
                "Two year",
                "Month-to-month",
            ],
            "PaymentMethod": [
                "Electronic check",
                "Mailed check",
                "Bank transfer (automatic)",
                "Credit card (automatic)",
                "Electronic check",
                "Mailed check",
                "Electronic check",
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
            "SeniorCitizen": [0, 1, 0, 1, 0, 1, 1],
            "gender": ["Female", "Male", "Female", "Male", "Female", "Male", "Female"],
        }
    )


def test_generate_eda_figures_writes_all_expected_observed_source_outputs(tmp_path: Path) -> None:
    """Every standard EDA visualization should be materialized as an image."""
    figures = eda.generate_eda_figures(_eda_data(), output_dir=tmp_path)

    assert [path.name for path in figures] == [
        "eda_churn_rate.png",
        "eda_tenure_analysis.png",
        "eda_monthly_charges.png",
        "eda_contract_type.png",
        "eda_payment_method.png",
        "eda_internet_service.png",
        "eda_support_ticket_proxy.png",
        "eda_correlation_heatmap.png",
        "eda_demographics.png",
    ]
    assert all(path.is_file() and path.stat().st_size > 1_000 for path in figures)


@pytest.mark.parametrize(
    "available_key",
    ["scored_data", "features_data", "scenario_data", "processed_data"],
)
def test_load_analysis_data_uses_the_richest_available_pipeline_output(
    tmp_path: Path,
    monkeypatch,
    available_key: str,
) -> None:
    """EDA should follow the documented scored-to-processed fallback order."""
    paths = {
        key: str(tmp_path / f"{key}.csv")
        for key in ("scored_data", "features_data", "scenario_data", "processed_data")
    }
    expected = pd.DataFrame({"selected": [available_key]})
    expected.to_csv(paths[available_key], index=False)
    monkeypatch.setattr(eda, "load_config", lambda: {"paths": paths})
    monkeypatch.setattr(eda, "resolve_path", Path)

    loaded = eda.load_analysis_data()

    pd.testing.assert_frame_equal(loaded, expected)


def test_load_analysis_data_explains_when_no_pipeline_output_exists(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The missing-output error should give an actionable recovery command."""
    paths = {
        key: str(tmp_path / f"{key}.csv")
        for key in ("scored_data", "features_data", "scenario_data", "processed_data")
    }
    monkeypatch.setattr(eda, "load_config", lambda: {"paths": paths})
    monkeypatch.setattr(eda, "resolve_path", Path)

    with pytest.raises(FileNotFoundError, match="Run run_pipeline.py first"):
        eda.load_analysis_data()


def test_select_observed_records_falls_back_without_usable_lineage() -> None:
    """Legacy or scenario-only data should retain all rows instead of becoming empty."""
    data = _eda_data()

    without_lineage, missing_excluded = eda.select_observed_records(
        data.drop(columns="record_source")
    )
    synthetic_only, synthetic_excluded = eda.select_observed_records(
        data.loc[data["record_source"].eq("synthetic_cohort")]
    )

    assert without_lineage.equals(data.drop(columns="record_source"))
    assert missing_excluded == 0
    assert synthetic_only.equals(data.loc[data["record_source"].eq("synthetic_cohort")])
    assert synthetic_excluded == 0


def test_eda_summary_honors_explicit_exclusion_count() -> None:
    """Pipeline callers can preserve the original scenario exclusion count."""
    summary = eda.generate_eda_summary(_eda_data(), excluded_scenario_records=42)

    assert "**Observed source customers analyzed:** 6" in summary
    assert "**Synthetic scenario records excluded from findings:** 42" in summary


def test_run_eda_writes_an_observed_source_summary(tmp_path: Path, monkeypatch) -> None:
    """The orchestration path passes only observed records into the figure stage."""
    generated_inputs: list[pd.DataFrame] = []
    monkeypatch.setattr(eda, "load_analysis_data", _eda_data)
    monkeypatch.setattr(
        eda,
        "generate_eda_figures",
        lambda data: generated_inputs.append(data.copy()) or [],
    )
    monkeypatch.setattr(eda, "resolve_path", lambda relative_path: tmp_path / relative_path)

    eda.run_eda()

    assert len(generated_inputs) == 1
    assert generated_inputs[0]["record_source"].eq("observed").all()
    summary = (tmp_path / "reports" / "eda_summary.md").read_text(encoding="utf-8")
    assert "**Observed source customers analyzed:** 6" in summary
    assert "**Synthetic scenario records excluded from findings:** 1" in summary


def test_support_proxy_plot_skips_absent_proxy_column(tmp_path: Path) -> None:
    """The optional proxy figure has a stable no-op result for legacy exports."""
    data_without_proxy = _eda_data().drop(columns="support_ticket_proxy")
    path = eda._plot_support_proxy(data_without_proxy, "Churn", tmp_path)

    assert path == tmp_path / "eda_support_ticket_proxy.png"
    assert not path.exists()
