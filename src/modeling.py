"""Model training, group-aware validation, and risk scoring utilities."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

import joblib
import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    StratifiedGroupKFold,
    StratifiedKFold,
    train_test_split,
)
from sklearn.pipeline import Pipeline

from src.config import load_config, resolve_path
from src.feature_engineering import build_preprocessor, get_feature_columns

logger = logging.getLogger(__name__)


@dataclass
class ModelingSplit:
    """Train/test partition with source IDs retained for leakage checks."""

    X_train: pd.DataFrame
    y_train: pd.Series
    X_test: pd.DataFrame
    y_test: pd.Series
    train_groups: pd.Series
    test_groups: pd.Series
    train_customer_ids: pd.Series
    test_customer_ids: pd.Series

    def __iter__(self) -> Iterator[pd.DataFrame | pd.Series]:
        """Allow legacy four-value unpacking in lightweight callers."""
        yield self.X_train
        yield self.y_train
        yield self.X_test
        yield self.y_test


@dataclass
class ModelResult:
    """Tuned candidate model and training-only cross-validation evidence."""

    name: str
    pipeline: Pipeline
    selection_score: float
    cv_metrics: dict[str, dict[str, Any]]
    best_params: dict[str, Any] = field(default_factory=dict)


def prepare_modeling_data(df: pd.DataFrame) -> ModelingSplit:
    """Create an observed-only holdout while preventing source-profile leakage.

    Scenario rows are intentionally excluded from the default model evidence:
    they are useful for visualizing a larger analytics dataset but are derived
    from the 7,043 observed source profiles and are not independent customers.
    """
    config = load_config()
    data_config = config["data"]
    churn_col = data_config["churn_column"]
    id_col = data_config["id_column"]
    source_col = data_config["source_id_column"]
    record_source_col = data_config["record_source_column"]
    observed_label = data_config["observed_label"]
    numeric, categorical = get_feature_columns()
    feature_columns = numeric + categorical

    missing_features = sorted(set(feature_columns) - set(df.columns))
    if missing_features:
        raise ValueError(f"Modeling data is missing feature columns: {missing_features}")
    if churn_col not in df.columns:
        raise ValueError(f"Modeling data is missing target column: {churn_col}")

    data = df.copy()
    if source_col not in data:
        data[source_col] = data[id_col].astype(str)
    if record_source_col in data:
        observed = data.loc[
            data[record_source_col].isin({observed_label, "original"})
        ].copy()
    else:
        observed = data.copy()
    if observed.empty:
        raise ValueError("No observed records are available for model training.")

    X = observed[feature_columns].copy()
    y = observed[churn_col].astype(int).copy()
    groups = observed[source_col].astype(str).copy()
    customer_ids = observed[id_col].astype(str).copy()
    test_size = float(data_config["test_size"])
    seed = config["project"]["random_seed"]

    has_repeated_sources = groups.nunique() < len(groups)
    if has_repeated_sources and 1 / test_size == round(1 / test_size):
        n_splits = int(round(1 / test_size))
        if groups.nunique() < n_splits:
            raise ValueError(
                "Source-disjoint validation requires at least one source group per holdout fold."
            )
        splitter = StratifiedGroupKFold(
            n_splits=n_splits,
            shuffle=True,
            random_state=seed,
        )
        train_indices, test_indices = next(splitter.split(X, y, groups))
        split_description = "group-aware, source-disjoint"
    else:
        train_indices, test_indices = train_test_split(
            np.arange(len(observed)),
            test_size=test_size,
            random_state=seed,
            stratify=y,
        )
        split_description = "stratified"

    split = ModelingSplit(
        X_train=X.iloc[train_indices].reset_index(drop=True),
        y_train=y.iloc[train_indices].reset_index(drop=True),
        X_test=X.iloc[test_indices].reset_index(drop=True),
        y_test=y.iloc[test_indices].reset_index(drop=True),
        train_groups=groups.iloc[train_indices].reset_index(drop=True),
        test_groups=groups.iloc[test_indices].reset_index(drop=True),
        train_customer_ids=customer_ids.iloc[train_indices].reset_index(drop=True),
        test_customer_ids=customer_ids.iloc[test_indices].reset_index(drop=True),
    )
    _validate_source_disjoint_split(split)
    logger.info(
        "Prepared observed-only %s split: %d train / %d test records.",
        split_description,
        len(split.X_train),
        len(split.X_test),
    )
    return split


def _validate_source_disjoint_split(split: ModelingSplit) -> None:
    """Raise if a source profile can appear in both training and holdout data."""
    overlap = set(split.train_groups) & set(split.test_groups)
    if overlap:
        raise RuntimeError(
            f"Source-group leakage detected across split ({len(overlap)} groups)."
        )


def get_model_search_spaces() -> dict[str, tuple[Any, dict[str, list[Any]], str, int]]:
    """Return estimators and deliberately bounded hyperparameter search spaces."""
    config = load_config()
    iterations = int(config["modeling"]["randomized_search_iterations"])
    spaces: dict[str, tuple[Any, dict[str, list[Any]], str, int]] = {
        "logistic_regression": (
            LogisticRegression(max_iter=2_000, random_state=42),
            {
                "classifier__C": [0.01, 0.1, 1.0, 10.0],
                "classifier__penalty": ["l2"],
                "classifier__solver": ["lbfgs"],
            },
            "grid",
            0,
        ),
        "random_forest": (
            RandomForestClassifier(
                class_weight="balanced_subsample",
                # Parameter-search folds are parallelized externally; keeping
                # each forest single-threaded avoids nested oversubscription.
                n_jobs=1,
                random_state=42,
            ),
            {
                "classifier__n_estimators": [200, 300, 400],
                "classifier__max_depth": [8, 12, 16, None],
                "classifier__min_samples_split": [2, 5, 10],
                "classifier__min_samples_leaf": [1, 2, 4],
                "classifier__max_features": ["sqrt", "log2", 0.5],
            },
            "randomized",
            iterations,
        ),
        "gradient_boosting": (
            GradientBoostingClassifier(random_state=42),
            {
                "classifier__n_estimators": [100, 200, 300],
                "classifier__learning_rate": [0.03, 0.05, 0.1],
                "classifier__max_depth": [2, 3, 4],
                "classifier__subsample": [0.7, 0.85, 1.0],
                "classifier__min_samples_leaf": [1, 3, 5],
            },
            "randomized",
            iterations,
        ),
    }
    if config["modeling"].get("enable_xgboost", False):
        spaces.update(_optional_xgboost_space(iterations))
    return spaces


def _optional_xgboost_space(
    iterations: int,
) -> dict[str, tuple[Any, dict[str, list[Any]], str, int]]:
    """Load the optional XGBoost candidate only when it is explicitly enabled."""
    try:
        from xgboost import XGBClassifier
    except ImportError as error:
        logger.warning("XGBoost requested but unavailable: %s", error)
        return {}
    return {
        "xgboost": (
            XGBClassifier(
                eval_metric="logloss",
                n_jobs=-1,
                random_state=42,
            ),
            {
                "classifier__n_estimators": [150, 250, 350],
                "classifier__max_depth": [3, 4, 5],
                "classifier__learning_rate": [0.03, 0.05, 0.1],
                "classifier__subsample": [0.7, 0.85, 1.0],
                "classifier__colsample_bytree": [0.6, 0.8, 1.0],
                "classifier__reg_lambda": [0.5, 1.0, 2.0],
            },
            "randomized",
            iterations,
        )
    }


def build_pipeline(estimator: Any) -> Pipeline:
    """Create a complete preprocessing-and-classification pipeline."""
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("classifier", estimator),
        ]
    )


def train_models(
    df: pd.DataFrame,
    model_names: list[str] | None = None,
) -> tuple[dict[str, ModelResult], ModelingSplit]:
    """Tune candidates on training folds and select without touching the holdout."""
    config = load_config()
    split = prepare_modeling_data(df)
    search_spaces = get_model_search_spaces()
    requested_names = model_names or list(config["modeling"]["models"])
    if config["modeling"].get("enable_xgboost", False) and "xgboost" not in requested_names:
        requested_names.append("xgboost")
    cv = _build_group_cv(config, split.train_groups)
    uses_group_cv = isinstance(cv, StratifiedGroupKFold)
    results: dict[str, ModelResult] = {}

    for name in requested_names:
        if name not in search_spaces:
            logger.warning("Unknown or unavailable model '%s'; skipping.", name)
            continue
        estimator, parameter_space, search_type, n_iter = search_spaces[name]
        search = _make_search(
            build_pipeline(estimator),
            parameter_space,
            search_type,
            n_iter,
            cv,
            config,
        )
        logger.info("Tuning %s using training data only.", name)
        fit_kwargs = {"groups": split.train_groups} if uses_group_cv else {}
        search.fit(split.X_train, split.y_train, **fit_kwargs)

        from src.evaluation import run_cross_validation

        cv_metrics = run_cross_validation(
            search.best_estimator_,
            split.X_train,
            split.y_train,
            groups=split.train_groups if uses_group_cv else None,
        )
        results[name] = ModelResult(
            name=name,
            pipeline=search.best_estimator_,
            selection_score=float(search.best_score_),
            cv_metrics=cv_metrics,
            best_params=search.best_params_,
        )
        logger.info(
            "%s training CV ROC-AUC: %.3f",
            name,
            results[name].selection_score,
        )

    if not results:
        raise RuntimeError("No model candidates were trained.")
    _save_test_split(split)
    return results, split


def _build_group_cv(
    config: dict[str, Any],
    groups: pd.Series,
) -> StratifiedGroupKFold | StratifiedKFold:
    """Create stratified folds, preserving source groups when they repeat."""
    folds = min(int(config["modeling"]["cv_folds"]), int(groups.nunique()))
    if folds < 2:
        raise ValueError("At least two distinct source groups are required for CV.")
    if groups.nunique() == len(groups):
        return StratifiedKFold(
            n_splits=folds,
            shuffle=True,
            random_state=config["project"]["random_seed"],
        )
    return StratifiedGroupKFold(
        n_splits=folds,
        shuffle=True,
        random_state=config["project"]["random_seed"],
    )


def _make_search(
    pipeline: Pipeline,
    parameter_space: dict[str, list[Any]],
    search_type: str,
    n_iter: int,
    cv: StratifiedGroupKFold | StratifiedKFold,
    config: dict[str, Any],
) -> GridSearchCV | RandomizedSearchCV:
    """Instantiate a reproducible parameter search object."""
    common = {
        "cv": cv,
        "error_score": "raise",
        "n_jobs": config["modeling"]["n_jobs"],
        "refit": True,
        "scoring": config["modeling"]["scoring"],
    }
    if search_type == "grid":
        return GridSearchCV(pipeline, param_grid=parameter_space, **common)
    return RandomizedSearchCV(
        pipeline,
        param_distributions=parameter_space,
        n_iter=n_iter,
        random_state=config["project"]["random_seed"],
        **common,
    )


def select_best_model(results: dict[str, ModelResult]) -> ModelResult:
    """Select the candidate with the best training-only CV ROC-AUC."""
    return max(results.values(), key=lambda result: result.selection_score)


def score_analytics_scenario(
    scenario: pd.DataFrame,
    pipeline: Pipeline,
    model_name: str,
) -> pd.DataFrame:
    """Attach source-out-of-fold churn probabilities to all scenario records.

    Each observed source customer and every scenario profile derived from it is
    scored by a model that did not train on that source.  This prevents in-sample
    probabilities from being presented as validated dashboard risk scores.
    """
    config = load_config()
    data_config = config["data"]
    id_col = data_config["id_column"]
    source_col = data_config["source_id_column"]
    record_source_col = data_config["record_source_column"]
    churn_col = data_config["churn_column"]
    observed_label = data_config["observed_label"]
    numeric, categorical = get_feature_columns()
    feature_columns = numeric + categorical

    scored = scenario.copy()
    observed_mask = scored[record_source_col].isin({observed_label, "original"})
    observed = scored.loc[observed_mask].copy()
    probabilities = pd.Series(np.nan, index=scored.index, dtype=float)
    observed_X = observed[feature_columns].reset_index(drop=True)
    observed_y = observed[churn_col].astype(int).reset_index(drop=True)
    observed_sources = observed[source_col].astype(str).reset_index(drop=True)
    has_repeated_sources = observed_sources.nunique() < len(observed_sources)
    fold_count = min(
        int(config["modeling"]["cv_folds"]),
        int(observed_sources.nunique()) if has_repeated_sources else len(observed),
    )
    if fold_count < 2:
        raise ValueError(
            "At least two observed source profiles are required for out-of-fold scoring."
        )
    if has_repeated_sources:
        splitter = StratifiedGroupKFold(
            n_splits=fold_count,
            shuffle=True,
            random_state=config["project"]["random_seed"],
        )
        fold_iterator = splitter.split(observed_X, observed_y, observed_sources)
    else:
        splitter = StratifiedKFold(
            n_splits=fold_count,
            shuffle=True,
            random_state=config["project"]["random_seed"],
        )
        fold_iterator = splitter.split(observed_X, observed_y)

    for train_indices, validation_indices in fold_iterator:
        fold_model = clone(pipeline)
        fold_model.fit(observed_X.iloc[train_indices], observed_y.iloc[train_indices])
        validation_sources = set(observed_sources.iloc[validation_indices])
        scenario_mask = scored[source_col].astype(str).isin(validation_sources)
        probabilities.loc[scenario_mask] = fold_model.predict_proba(
            scored.loc[scenario_mask, feature_columns]
        )[:, 1]

    if probabilities.isna().any():
        raise RuntimeError("Unable to produce an out-of-fold score for every scenario row.")

    threshold = float(config["modeling"]["risk_threshold"])
    scored["churn_probability"] = probabilities.round(4)
    # Tableau uses the explicit `predicted_` label; SQLite keeps the shorter
    # canonical prediction-table field name above.
    scored["predicted_churn_probability"] = scored["churn_probability"]
    scored["risk_band"] = assign_risk_bands(scored["churn_probability"], threshold)
    scored["is_high_risk"] = (scored["churn_probability"] >= threshold).astype(int)
    scored["revenue_at_risk"] = (
        scored["MonthlyCharges"] * scored["churn_probability"]
    ).round(2)
    scored["model_name"] = model_name
    scored["model_version"] = config["project"]["model_version"]
    scored["decision_threshold"] = threshold
    scored["score_source"] = "out_of_fold_observed_model"

    if scored[id_col].duplicated().any():
        raise RuntimeError("Scored scenario must retain unique customer IDs.")
    return scored


def assign_risk_bands(probabilities: pd.Series, threshold: float) -> pd.Series:
    """Assign mutually consistent Low, Medium, and High risk bands.

    The High band begins at the configured decision threshold so dashboard
    banding, high-risk counts, and retention worklists use one definition.
    """
    if not 0.35 < threshold <= 1.0:
        raise ValueError("Risk threshold must be greater than 0.35 and no greater than 1.0.")
    return pd.cut(
        probabilities,
        bins=[-np.inf, 0.35, threshold, np.inf],
        labels=["Low", "Medium", "High"],
        right=False,
        include_lowest=True,
    ).astype(str)


def save_models(
    results: dict[str, ModelResult],
    output_dir: Path | None = None,
) -> Path:
    """Persist fitted candidate pipelines and their training-only evidence."""
    config = load_config()
    directory = output_dir or resolve_path(config["paths"]["models_dir"])
    directory.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {}

    for name, result in results.items():
        joblib.dump(result.pipeline, directory / f"{name}.joblib")
        summary[name] = {
            "selection_metric": config["modeling"]["scoring"],
            "selection_score": result.selection_score,
            "cross_validation": result.cv_metrics,
            "best_params": result.best_params,
        }

    summary_path = directory / "model_metrics.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("Saved %d model artifacts to %s", len(results), directory)
    return directory


def _save_test_split(split: ModelingSplit) -> Path:
    """Persist an auditable holdout contract without feature leakage."""
    path = resolve_path("data/processed/test_holdout.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    holdout = split.X_test.copy()
    holdout["source_customer_id"] = split.test_groups.to_numpy()
    holdout["customerID"] = split.test_customer_ids.to_numpy()
    holdout["Churn"] = split.y_test.to_numpy()
    holdout.to_csv(path, index=False)
    return path
