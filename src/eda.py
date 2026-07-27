"""Repeatable exploratory analysis and publication-quality visual outputs."""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.config import load_config, resolve_path

logger = logging.getLogger(__name__)

plt.style.use("seaborn-v0_8-whitegrid")
RETAINED_COLOR = "#0f766e"
CHURNED_COLOR = "#dc2626"
ACCENT_COLOR = "#2563eb"


def load_analysis_data() -> pd.DataFrame:
    """Load the richest available pipeline output for EDA."""
    config = load_config()
    for key in ("scored_data", "features_data", "scenario_data", "processed_data"):
        path = resolve_path(config["paths"][key])
        if path.exists():
            return pd.read_csv(path)
    raise FileNotFoundError("No pipeline output found. Run run_pipeline.py first.")


def generate_eda_figures(
    df: pd.DataFrame,
    output_dir: Path | None = None,
) -> list[Path]:
    """Generate core segmentation, behavior, and correlation figures."""
    config = load_config()
    figures_dir = output_dir or resolve_path(config["paths"]["figures_dir"])
    figures_dir.mkdir(parents=True, exist_ok=True)
    churn_col = config["data"]["churn_column"]

    figures = [
        _plot_churn_rate(df, churn_col, figures_dir),
        _plot_tenure_analysis(df, churn_col, figures_dir),
        _plot_monthly_charges(df, churn_col, figures_dir),
        _plot_contract_churn(df, churn_col, figures_dir),
        _plot_payment_method(df, churn_col, figures_dir),
        _plot_internet_service(df, churn_col, figures_dir),
        _plot_support_proxy(df, churn_col, figures_dir),
        _plot_correlation_heatmap(df, figures_dir),
        _plot_demographics(df, churn_col, figures_dir),
    ]
    logger.info("Generated %d EDA figures in %s", len(figures), figures_dir)
    return figures


def _save_figure(figure: plt.Figure, path: Path) -> Path:
    """Save a consistently styled figure and release its memory."""
    figure.tight_layout()
    figure.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(figure)
    return path


def _plot_churn_rate(df: pd.DataFrame, churn_col: str, output_dir: Path) -> Path:
    path = output_dir / "eda_churn_rate.png"
    churn_rate = float(df[churn_col].mean() * 100)
    figure, axis = plt.subplots(figsize=(6, 4))
    axis.bar(
        ["Retained", "Churned"],
        [100 - churn_rate, churn_rate],
        color=[RETAINED_COLOR, CHURNED_COLOR],
    )
    axis.set(ylabel="Customers (%)", ylim=(0, 100), title=f"Observed Churn Rate: {churn_rate:.1f}%")
    for index, value in enumerate([100 - churn_rate, churn_rate]):
        axis.text(index, value + 2, f"{value:.1f}%", ha="center", fontweight="bold")
    return _save_figure(figure, path)


def _plot_tenure_analysis(df: pd.DataFrame, churn_col: str, output_dir: Path) -> Path:
    path = output_dir / "eda_tenure_analysis.png"
    plotting_data = df.copy()
    plotting_data["Churn status"] = plotting_data[churn_col].map(
        {0: "Retained", 1: "Churned"}
    )
    figure, axis = plt.subplots(figsize=(10, 5))
    sns.histplot(
        data=plotting_data,
        x="tenure",
        hue="Churn status",
        bins=24,
        stat="density",
        common_norm=False,
        element="step",
        palette={"Retained": RETAINED_COLOR, "Churned": CHURNED_COLOR},
        ax=axis,
    )
    axis.set(xlabel="Tenure (months)", ylabel="Density")
    axis.set_title("Tenure Distribution by Observed Churn")
    return _save_figure(figure, path)


def _plot_monthly_charges(df: pd.DataFrame, churn_col: str, output_dir: Path) -> Path:
    path = output_dir / "eda_monthly_charges.png"
    plotting_data = df.copy()
    plotting_data["Churn status"] = plotting_data[churn_col].map(
        {0: "Retained", 1: "Churned"}
    )
    figure, axis = plt.subplots(figsize=(8, 5))
    sns.boxplot(
        data=plotting_data,
        x="Churn status",
        y="MonthlyCharges",
        hue="Churn status",
        legend=False,
        palette={"Retained": RETAINED_COLOR, "Churned": CHURNED_COLOR},
        ax=axis,
    )
    axis.set(xlabel="Observed churn status", ylabel="Monthly charges ($)")
    axis.set_title("Monthly Charges by Observed Churn")
    return _save_figure(figure, path)


def _plot_contract_churn(df: pd.DataFrame, churn_col: str, output_dir: Path) -> Path:
    path = output_dir / "eda_contract_type.png"
    churn_by_contract = df.groupby("Contract", observed=True)[churn_col].mean().sort_values()
    figure, axis = plt.subplots(figsize=(8, 5))
    churn_by_contract.mul(100).plot(kind="barh", color=ACCENT_COLOR, ax=axis)
    axis.set(xlabel="Observed churn rate (%)", ylabel="Contract")
    axis.set_title("Observed Churn Rate by Contract Type")
    return _save_figure(figure, path)


def _plot_payment_method(df: pd.DataFrame, churn_col: str, output_dir: Path) -> Path:
    path = output_dir / "eda_payment_method.png"
    churn_by_payment = (
        df.groupby("PaymentMethod", observed=True)[churn_col].mean().sort_values()
    )
    figure, axis = plt.subplots(figsize=(10, 5))
    churn_by_payment.mul(100).plot(kind="barh", color="#7c3aed", ax=axis)
    axis.set(xlabel="Observed churn rate (%)", ylabel="Payment method")
    axis.set_title("Observed Churn Rate by Payment Method")
    return _save_figure(figure, path)


def _plot_internet_service(df: pd.DataFrame, churn_col: str, output_dir: Path) -> Path:
    path = output_dir / "eda_internet_service.png"
    churn_by_internet = (
        df.groupby("InternetService", observed=True)[churn_col].mean().sort_values()
    )
    figure, axis = plt.subplots(figsize=(8, 5))
    churn_by_internet.mul(100).plot(kind="bar", color="#0891b2", ax=axis)
    axis.set(xlabel="Internet service", ylabel="Observed churn rate (%)")
    axis.set_title("Observed Churn Rate by Internet Service")
    axis.tick_params(axis="x", rotation=12)
    return _save_figure(figure, path)


def _plot_support_proxy(df: pd.DataFrame, churn_col: str, output_dir: Path) -> Path:
    path = output_dir / "eda_support_ticket_proxy.png"
    proxy_column = "support_ticket_proxy"
    if proxy_column not in df:
        return path
    summary = df.groupby(proxy_column, observed=True)[churn_col].agg(["mean", "count"])
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.bar(summary.index.astype(str), summary["mean"] * 100, color="#f59e0b")
    axis.set(
        xlabel="Estimated support-ticket proxy",
        ylabel="Observed churn rate (%)",
        title="Observed Churn by Estimated Support-Need Proxy",
    )
    return _save_figure(figure, path)


def _plot_correlation_heatmap(df: pd.DataFrame, output_dir: Path) -> Path:
    path = output_dir / "eda_correlation_heatmap.png"
    requested_columns = [
        "tenure",
        "MonthlyCharges",
        "TotalCharges",
        "revenue_per_month",
        "service_count",
        "support_ticket_proxy",
        "customer_engagement_score",
        "support_intensity",
        "Churn",
    ]
    available_columns = [column for column in requested_columns if column in df.columns]
    correlation = df[available_columns].corr(numeric_only=True)
    figure, axis = plt.subplots(figsize=(10, 8))
    sns.heatmap(correlation, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=axis)
    axis.set_title("Correlation Matrix for Numeric Snapshot Features")
    return _save_figure(figure, path)


def _plot_demographics(df: pd.DataFrame, churn_col: str, output_dir: Path) -> Path:
    path = output_dir / "eda_demographics.png"
    plotting_data = df.copy()
    plotting_data["Senior status"] = plotting_data["SeniorCitizen"].map(
        {1: "Senior (65+)", 0: "Non-senior"}
    )
    senior_churn = plotting_data.groupby("Senior status", observed=True)[churn_col].mean()
    gender_churn = plotting_data.groupby("gender", observed=True)[churn_col].mean()
    figure, axes = plt.subplots(1, 2, figsize=(12, 5))
    senior_churn.mul(100).plot(kind="bar", color="#f59e0b", ax=axes[0])
    gender_churn.mul(100).plot(kind="bar", color="#6366f1", ax=axes[1])
    axes[0].set(title="Observed Churn by Senior Status", ylabel="Churn rate (%)")
    axes[1].set(title="Observed Churn by Gender", ylabel="Churn rate (%)")
    for axis in axes:
        axis.tick_params(axis="x", rotation=0)
    return _save_figure(figure, path)


def generate_eda_summary(df: pd.DataFrame) -> str:
    """Create a values-driven Markdown summary with appropriately bounded claims."""
    churn_rate = float(df["Churn"].mean() * 100)
    contract_rates = df.groupby("Contract", observed=True)["Churn"].mean().sort_values(
        ascending=False
    )
    internet_rates = df.groupby("InternetService", observed=True)["Churn"].mean().sort_values(
        ascending=False
    )
    payment_rates = df.groupby("PaymentMethod", observed=True)["Churn"].mean().sort_values(
        ascending=False
    )
    onboarding_rate = float(df.loc[df["tenure"] <= 6, "Churn"].mean() * 100)
    mature_rate = float(df.loc[df["tenure"] > 24, "Churn"].mean() * 100)
    source_counts = (
        df["record_source"].value_counts().to_dict()
        if "record_source" in df.columns
        else {"observed": len(df)}
    )

    lines = [
        "# Exploratory Data Analysis Summary",
        "",
        "## Scope",
        "",
        f"- **Customer records analyzed:** {len(df):,}",
        f"- **Observed source records:** {source_counts.get('observed', 0):,}",
        f"- **Synthetic cohort scenario records:** {source_counts.get('synthetic_cohort', 0):,}",
        f"- **Observed churn rate:** {churn_rate:.1f}%",
        f"- **Average tenure:** {df['tenure'].mean():.1f} months",
        f"- **Average monthly charge (MRR proxy):** ${df['MonthlyCharges'].mean():,.2f}",
        "",
        "## Segment findings",
        "",
        f"1. **{contract_rates.index[0]}** customers have the highest observed churn "
        f"rate ({contract_rates.iloc[0] * 100:.1f}%).",
        f"2. **{internet_rates.index[0]}** customers have the highest observed churn "
        f"rate among internet-service groups ({internet_rates.iloc[0] * 100:.1f}%).",
        f"3. Customers in the **0–6 month onboarding window** show {onboarding_rate:.1f}% "
        f"observed churn, versus {mature_rate:.1f}% for customers beyond 24 months.",
        f"4. **{payment_rates.index[0]}** has the highest observed churn rate among "
        f"payment methods ({payment_rates.iloc[0] * 100:.1f}%).",
        "5. The estimated support-ticket measure is a service-configuration proxy, not "
        "an observed ticket count; use it for segmentation hypotheses only.",
        "",
        "## Interpretation guardrails",
        "",
        "- The source is a cross-sectional customer snapshot. It does not establish "
        "causality, true acquisition cohorts, or month-over-month revenue trends.",
        "- The synthetic cohort rows preserve the observed population mix for scalable "
        "dashboard exploration, but they are not additional independent customers.",
        "- `MonthlyCharges` and lifetime-value fields are revenue and value proxies, not "
        "audited financial statements.",
    ]
    return "\n".join(lines)


def run_eda(data: pd.DataFrame | None = None) -> None:
    """Generate figures and a Markdown summary from the latest pipeline output."""
    analysis_data = data if data is not None else load_analysis_data()
    generate_eda_figures(analysis_data)
    summary_path = resolve_path("reports/eda_summary.md")
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(generate_eda_summary(analysis_data), encoding="utf-8")
    logger.info("EDA summary written to %s", summary_path)
