"""Tests for stratified, source-aware splitting, model pipelines, and risk scoring."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

import src.evaluation as evaluation
from src.config import load_config
from src.evaluation import compute_metrics
from src.feature_engineering import build_preprocessor, engineer_features, get_feature_columns
from src.modeling import (
    assign_risk_bands,
    build_pipeline,
    prepare_modeling_data,
    score_analytics_scenario,
)
from src.preprocessing import augment_dataset, clean_data, load_raw_data


class _BoundaryProbabilityModel:
    """Return probabilities that round to the threshold from opposite sides."""

    def fit(self, X: pd.DataFrame, y: pd.Series) -> _BoundaryProbabilityModel:
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        probabilities = np.full(len(X), 0.25)
        monthly_charges = X["MonthlyCharges"].to_numpy()
        probabilities[np.isclose(monthly_charges, 199.0)] = 0.49996
        probabilities[np.isclose(monthly_charges, 200.0)] = 0.50004
        return np.column_stack([1 - probabilities, probabilities])


class _ConfiguredThresholdModel:
    """Expose a deliberate conflict between estimator and configured decisions."""

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        raise AssertionError("Evaluation must derive predictions from configured threshold.")

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        probabilities = np.array([0.55, 0.60, 0.65])
        return np.column_stack([1 - probabilities, probabilities])


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


def test_scoring_uses_unrounded_probabilities_for_decisions_and_revenue(
    featured_observed_data: pd.DataFrame,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = featured_observed_data.copy()
    scenario.loc[0, "MonthlyCharges"] = 199.0
    scenario.loc[1, "MonthlyCharges"] = 200.0
    model = _BoundaryProbabilityModel()
    monkeypatch.setattr("src.modeling.clone", lambda _: model)

    scored = score_analytics_scenario(scenario, model, "boundary")

    below_threshold = scored.loc[0]
    above_threshold = scored.loc[1]
    assert below_threshold["churn_probability"] == pytest.approx(0.5)
    assert above_threshold["churn_probability"] == pytest.approx(0.5)
    assert below_threshold["risk_band"] == "Medium"
    assert below_threshold["is_high_risk"] == 0
    assert below_threshold["revenue_at_risk"] == pytest.approx(99.49)
    assert above_threshold["risk_band"] == "High"
    assert above_threshold["is_high_risk"] == 1
    assert above_threshold["revenue_at_risk"] == pytest.approx(100.01)


def test_evaluation_uses_the_configured_threshold_for_predictions_and_report(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = load_config()
    config["modeling"]["risk_threshold"] = 0.60
    monkeypatch.setattr(evaluation, "load_config", lambda: config)
    monkeypatch.setattr(evaluation, "resolve_path", lambda _: tmp_path / "reports")
    monkeypatch.setattr(
        evaluation,
        "compute_feature_importance",
        lambda *_: pd.DataFrame(
            {
                "feature": ["MonthlyCharges"],
                "importance_mean": [0.1],
                "importance_std": [0.0],
            }
        ),
    )
    for function_name in (
        "plot_roc_curve",
        "plot_precision_recall_curve",
        "plot_confusion_matrix",
        "plot_calibration_curve",
        "plot_feature_importance",
    ):
        monkeypatch.setattr(evaluation, function_name, lambda *_args, **_kwargs: tmp_path)

    report = evaluation.generate_evaluation_report(
        _ConfiguredThresholdModel(),
        pd.DataFrame({"MonthlyCharges": [10.0, 20.0, 30.0]}),
        pd.Series([0, 1, 1]),
        "configured-threshold-test",
        output_dir=tmp_path / "figures",
    )

    assert report["evaluation_protocol"]["threshold"] == pytest.approx(0.60)
    assert report["holdout_metrics"]["accuracy"] == pytest.approx(1.0)
    assert report["classification_report"]["1"]["recall"] == pytest.approx(1.0)
