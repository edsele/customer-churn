"""Tests for observed-source reporting defaults and transparent summaries."""

from __future__ import annotations

import pandas as pd

from src.config import load_config
from src.dashboard_preview import _select_observed_snapshot
from src.eda import generate_eda_summary, select_observed_records
from src.feature_engineering import engineer_features
from src.preprocessing import augment_dataset, clean_data, load_raw_data


def _scenario_fixture() -> pd.DataFrame:
    raw = load_raw_data()
    observed = clean_data(
        pd.concat(
            [raw.loc[raw["Churn"] == "Yes"].head(20), raw.loc[raw["Churn"] == "No"].head(40)],
            ignore_index=True,
        )
    )
    return engineer_features(augment_dataset(observed, target_records=120, random_seed=3))


def test_reporting_defaults_to_observed_source_records() -> None:
    scenario = _scenario_fixture()

    observed, excluded_count = select_observed_records(scenario)
    preview_data, scope = _select_observed_snapshot(scenario, load_config())

    assert len(observed) == 60
    assert excluded_count == 60
    assert len(preview_data) == len(observed)
    assert scope == "observed-source snapshot (n=60)"


def test_eda_summary_discloses_excluded_scenario_records() -> None:
    scenario = _scenario_fixture()

    summary = generate_eda_summary(scenario)

    assert "**Observed source customers analyzed:** 60" in summary
    assert "**Synthetic scenario records excluded from findings:** 60" in summary
