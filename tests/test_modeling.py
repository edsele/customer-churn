"""Tests for stratified, source-aware splitting, model pipelines, and risk scoring."""

from __future__ import annotations

import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from src.evaluation import compute_metrics
from src.feature_engineering import build_preprocessor, engineer_features, get_feature_columns
from src.modeling import (
    assign_risk_bands,
    build_pipeline,
    prepare_modeling_data,
    score_analytics_scenario,
)
from src.preprocessing import augment_dataset, clean_data, load_raw_data


@pytest.fixture(scope="module")
def featured_observed_data() -> pd.DataFrame:
    """A compact but class-balanced observed sample for fast model-contract tests."""
    raw = load_raw_data()
    positives = raw.loc[raw["Churn"] == "Yes"].head(120)
    negatives = raw.loc[raw["Churn"] == "No"].head(240)
    return engineer_features(clean_data(pd.concat([positives, negatives], ignore_index=True)))


def test_prepare_modeling_data_is_stratified_and_source_nonoverlapping(
    featured_observed_data: pd.DataFrame,
) -> None:
    split = prepare_modeling_data(featured_observed_data)
    assert len(split.X_train) + len(split.X_test) == len(featured_observed_data)
    assert len(split.X_train) == len(split.y_train)
    assert len(split.X_test) == len(split.y_test)
    assert not (set(split.train_groups) & set(split.test_groups))
    assert set(split.y_train.unique()).issubset({0, 1})
    assert split.y_test.mean() == pytest.approx(featured_observed_data["Churn"].mean())


def test_synthetic_rows_are_excluded_from_default_model_population(
    featured_observed_data: pd.DataFrame,
) -> None:
    scenario = engineer_features(
        augment_dataset(featured_observed_data, target_records=600, random_seed=9)
    )
    split = prepare_modeling_data(scenario)
    assert len(split.X_train) + len(split.X_test) == len(featured_observed_data)


def test_build_pipeline_fits_and_predicts(featured_observed_data: pd.DataFrame) -> None:
    split = prepare_modeling_data(featured_observed_data)
    pipeline = build_pipeline(DummyClassifier(strategy="prior"))
    pipeline.fit(split.X_train, split.y_train)
    predictions = pipeline.predict(split.X_test)
    probabilities = pipeline.predict_proba(split.X_test)[:, 1]
    assert len(predictions) == len(split.y_test)
    assert probabilities.min() >= 0
    assert probabilities.max() <= 1


def test_compute_metrics_returns_expected_keys(featured_observed_data: pd.DataFrame) -> None:
    split = prepare_modeling_data(featured_observed_data)
    pipeline = build_pipeline(DummyClassifier(strategy="prior"))
    pipeline.fit(split.X_train, split.y_train)
    metrics = compute_metrics(
        split.y_test,
        pipeline.predict(split.X_test),
        pipeline.predict_proba(split.X_test)[:, 1],
    )
    assert {"accuracy", "precision", "recall", "f1", "roc_auc"}.issubset(metrics)
    assert 0 <= metrics["accuracy"] <= 1


def test_preprocessor_output(featured_observed_data: pd.DataFrame) -> None:
    numeric, categorical = get_feature_columns()
    preprocessor = build_preprocessor()
    matrix = preprocessor.fit_transform(featured_observed_data[numeric + categorical])
    assert matrix.shape[0] == len(featured_observed_data)
    assert matrix.shape[1] > len(numeric)


def test_out_of_fold_scenario_scoring_has_complete_probability_contract(
    featured_observed_data: pd.DataFrame,
) -> None:
    scenario = engineer_features(
        augment_dataset(featured_observed_data, target_records=600, random_seed=22)
    )
    split = prepare_modeling_data(featured_observed_data)
    pipeline = build_pipeline(DummyClassifier(strategy="prior"))
    pipeline.fit(split.X_train, split.y_train)
    scored = score_analytics_scenario(scenario, pipeline, "dummy")
    assert scored["churn_probability"].between(0, 1).all()
    assert scored["predicted_churn_probability"].equals(scored["churn_probability"])
    assert set(scored["risk_band"]).issubset({"Low", "Medium", "High"})
    assert set(scored["score_source"]) == {"out_of_fold_observed_model"}


def test_out_of_fold_scoring_keeps_repeated_source_profiles_together(
    featured_observed_data: pd.DataFrame,
) -> None:
    scenario = featured_observed_data.copy()
    duplicate = scenario.iloc[[0]].copy()
    duplicate["customerID"] = "DUPLICATE-SOURCE"
    scenario = pd.concat([scenario, duplicate], ignore_index=True)

    split = prepare_modeling_data(featured_observed_data)
    pipeline = build_pipeline(DummyClassifier(strategy="prior"))
    pipeline.fit(split.X_train, split.y_train)
    scored = score_analytics_scenario(scenario, pipeline, "dummy")

    repeated_source = featured_observed_data.iloc[0]["source_customer_id"]
    repeated_scores = scored.loc[
        scored["source_customer_id"] == repeated_source,
        "churn_probability",
    ]
    assert len(repeated_scores) == 2
    assert repeated_scores.nunique() == 1


def test_risk_bands_match_the_high_risk_threshold() -> None:
    probabilities = pd.Series([0.0, 0.3499, 0.35, 0.4999, 0.5, 1.0])
    bands = assign_risk_bands(probabilities, threshold=0.5)

    assert bands.tolist() == ["Low", "Low", "Medium", "Medium", "High", "High"]
    assert (bands.eq("High") == probabilities.ge(0.5)).all()
