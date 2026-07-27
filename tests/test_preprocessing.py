"""Tests for data quality, cleaning, scenario construction, and features."""

from __future__ import annotations

import pandas as pd
import pytest

from src.feature_engineering import (
    create_tenure_bucket,
    engineer_features,
    get_feature_columns,
)
from src.preprocessing import (
    assess_scenario_distribution,
    augment_dataset,
    clean_data,
    load_raw_data,
    validate_data,
)


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    """Representative raw rows with both churn classes and a blank total charge."""
    rows = []
    for index in range(8):
        churn = "Yes" if index in {2, 6} else "No"
        tenure = index * 4
        rows.append(
            {
                "customerID": f"{1000 + index}-SAMPLE",
                "gender": "Male" if index % 2 else "Female",
                "SeniorCitizen": int(index % 3 == 0),
                "Partner": "Yes" if index % 2 else "No",
                "Dependents": "No" if index % 3 else "Yes",
                "tenure": tenure,
                "PhoneService": "Yes",
                "MultipleLines": "Yes" if index % 2 else "No",
                "InternetService": "Fiber optic" if index % 2 else "DSL",
                "OnlineSecurity": "No" if index % 2 else "Yes",
                "OnlineBackup": "Yes",
                "DeviceProtection": "No",
                "TechSupport": "No" if index % 2 else "Yes",
                "StreamingTV": "Yes" if index % 2 else "No",
                "StreamingMovies": "No",
                "Contract": "Month-to-month" if index % 2 else "One year",
                "PaperlessBilling": "Yes",
                "PaymentMethod": "Electronic check" if index % 2 else "Mailed check",
                "MonthlyCharges": 40.0 + index,
                "TotalCharges": " " if index == 0 else str((40.0 + index) * tenure),
                "Churn": churn,
            }
        )
    return pd.DataFrame(rows)


def test_load_raw_data_exists() -> None:
    data = load_raw_data()
    assert len(data) == 7_043
    assert "customerID" in data.columns


def test_validate_raw_data_passes() -> None:
    report = validate_data(load_raw_data())
    assert report.passed
    assert report.invalid_churn_values == 0
    assert report.range_violations == {}
    assert report.coercion_failures == {}


def test_validate_rejects_nonblank_numeric_coercion_failures(
    sample_raw_df: pd.DataFrame,
) -> None:
    malformed = sample_raw_df.copy()
    malformed["MonthlyCharges"] = malformed["MonthlyCharges"].astype(object)
    malformed.loc[1, "MonthlyCharges"] = "not-a-number"

    report = validate_data(malformed)

    assert not report.passed
    assert report.coercion_failures == {"MonthlyCharges": 1}
    assert "Nonblank numeric values could not be parsed." in report.messages


def test_clean_data_handles_blank_total_charges(sample_raw_df: pd.DataFrame) -> None:
    cleaned = clean_data(sample_raw_df)
    assert cleaned["TotalCharges"].isna().sum() == 0
    assert cleaned.loc[0, "TotalCharges"] == pytest.approx(0.0)
    assert set(cleaned["record_source"]) == {"observed"}
    assert cleaned["source_customer_id"].equals(cleaned["customerID"])


def test_clean_data_removes_duplicate_customer_ids(sample_raw_df: pd.DataFrame) -> None:
    duplicate_data = pd.concat([sample_raw_df, sample_raw_df.iloc[[0]]], ignore_index=True)
    cleaned = clean_data(duplicate_data)
    assert len(cleaned) == len(sample_raw_df)


def test_augmentation_is_deterministic_and_preserves_churn_prevalence(
    sample_raw_df: pd.DataFrame,
) -> None:
    observed = clean_data(sample_raw_df)
    first = augment_dataset(observed, target_records=100, random_seed=42)
    second = augment_dataset(observed, target_records=100, random_seed=42)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 100
    assert first["customerID"].is_unique
    assert (first["record_source"] == "observed").sum() == len(observed)
    assert first["source_customer_id"].isin(observed["customerID"]).all()
    assert first["Churn"].mean() == pytest.approx(observed["Churn"].mean(), abs=0.01)


def test_scenario_distribution_report_is_transparent(sample_raw_df: pd.DataFrame) -> None:
    observed = clean_data(sample_raw_df)
    scenario = augment_dataset(observed, target_records=80, random_seed=7)
    checks = assess_scenario_distribution(observed, scenario)
    assert abs(checks["churn_rate_delta"]) < 0.02
    assert "monthly_charge_mean_delta" in checks
    assert "Contract_max_distribution_delta" in checks
    assert "InternetService_max_distribution_delta" in checks
    assert "PaymentMethod_max_distribution_delta" in checks


def test_support_proxy_is_not_target_derived(sample_raw_df: pd.DataFrame) -> None:
    cleaned = clean_data(sample_raw_df)
    flipped = cleaned.copy()
    flipped["Churn"] = 1 - flipped["Churn"]
    original_features = engineer_features(cleaned)
    flipped_features = engineer_features(flipped)
    target_independent = [
        "support_ticket_proxy",
        "support_intensity",
        "customer_engagement_score",
        "service_count",
    ]
    pd.testing.assert_frame_equal(
        original_features[target_independent],
        flipped_features[target_independent],
    )


def test_tenure_bucket_boundaries() -> None:
    assert create_tenure_bucket(3) == "0-6 onboarding"
    assert create_tenure_bucket(12) == "7-24 growth"
    assert create_tenure_bucket(36) == "25-48 mature"
    assert create_tenure_bucket(60) == "49+ loyal"


def test_engineered_features_and_model_columns(sample_raw_df: pd.DataFrame) -> None:
    featured = engineer_features(clean_data(sample_raw_df))
    numeric, categorical = get_feature_columns()
    expected_columns = {
        "tenure_bucket",
        "revenue_per_month",
        "service_count",
        "avg_services_purchased",
        "contract_risk_score",
        "customer_engagement_score",
        "support_ticket_proxy",
    }
    assert expected_columns.issubset(featured.columns)
    assert set(numeric + categorical).issubset(featured.columns)
    assert "support_ticket_proxy" not in numeric + categorical
    assert "support_intensity" not in numeric + categorical
