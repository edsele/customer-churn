"""Portable dashboard preview generated from the Tableau-ready export.

This is a repository preview of the intended executive layout, not a Tableau
workbook screenshot.  The Tableau build specification in ``dashboard/`` remains
the authoritative implementation guide for interactive behavior.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import load_config, resolve_path


def generate_executive_summary_preview(
    data: pd.DataFrame,
    output_path: Path | None = None,
) -> Path:
    """Render an executive dashboard layout from a scored customer snapshot."""
    config = load_config()
    path = output_path or resolve_path(config["paths"]["dashboard_preview"])
    path.parent.mkdir(parents=True, exist_ok=True)

    churn_rate = float(data["Churn"].mean())
    monthly_revenue = float(data["MonthlyCharges"].sum())
    average_ltv = float(data["lifetime_value_estimate"].mean())
    probability = data.get("predicted_churn_probability", data.get("churn_probability"))
    if probability is None:
        probability = pd.Series(np.nan, index=data.index)
    high_risk = int((probability >= config["modeling"]["risk_threshold"]).sum())
    revenue_at_risk = float((data["MonthlyCharges"] * probability.fillna(0)).sum())

    figure = plt.figure(figsize=(16, 9), facecolor="#f8fafc")
    grid = figure.add_gridspec(
        nrows=3,
        ncols=12,
        height_ratios=[1.2, 3.6, 3.1],
        hspace=0.65,
        wspace=0.55,
    )
    figure.text(
        0.05,
        0.965,
        "Customer Churn & Behavioral Analytics",
        fontsize=21,
        fontweight="bold",
        color="#0f172a",
    )
    figure.text(
        0.05,
        0.938,
        "Executive dashboard preview · historical snapshot · model scores are out-of-fold",
        fontsize=10,
        color="#475569",
    )

    kpis = [
        ("Observed churn", f"{churn_rate:.1%}", "Historical outcome"),
        ("MRR proxy", f"${monthly_revenue / 1_000_000:.2f}M", "Monthly charges snapshot"),
        ("Avg. CLV estimate", f"${average_ltv:,.0f}", "Directional value estimate"),
        (
            "High-risk customers",
            f"{high_risk:,}",
            f"Score ≥ {config['modeling']['risk_threshold']:.0%}",
        ),
        ("MRR at risk", f"${revenue_at_risk / 1_000_000:.2f}M", "Probability-weighted estimate"),
    ]
    for index, (title, value, subtitle) in enumerate(kpis):
        axis = figure.add_subplot(grid[0, index * 12 // 5 : (index + 1) * 12 // 5])
        axis.set_facecolor("white")
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_color("#e2e8f0")
        axis.text(0.06, 0.75, title, transform=axis.transAxes, fontsize=9, color="#475569")
        axis.text(
            0.06,
            0.40,
            value,
            transform=axis.transAxes,
            fontsize=20,
            fontweight="bold",
            color="#0f172a",
        )
        axis.text(0.06, 0.16, subtitle, transform=axis.transAxes, fontsize=7.5, color="#64748b")

    contract_axis = figure.add_subplot(grid[1, :5])
    contract_rate = data.groupby("Contract", observed=True)["Churn"].mean().sort_values()
    contract_axis.barh(contract_rate.index, contract_rate.values * 100, color="#2563eb")
    contract_axis.set(
        title="Observed churn by contract",
        xlabel="Observed churn rate (%)",
        xlim=(0, max(contract_rate.values * 100) * 1.18),
    )
    _style_axis(contract_axis)

    probability_axis = figure.add_subplot(grid[1, 5:9])
    probability_axis.hist(
        probability.dropna(),
        bins=np.linspace(0, 1, 21),
        color="#7c3aed",
        edgecolor="white",
    )
    probability_axis.axvline(
        config["modeling"]["risk_threshold"],
        color="#dc2626",
        linestyle="--",
        linewidth=1.5,
        label=f"High-risk threshold ({config['modeling']['risk_threshold']:.0%})",
    )
    probability_axis.set(
        title="Predicted churn probability distribution",
        xlabel="Out-of-fold probability",
        ylabel="Customer records",
    )
    probability_axis.legend(fontsize=8, frameon=False)
    _style_axis(probability_axis)

    risk_axis = figure.add_subplot(grid[1, 9:])
    risk_source = data.assign(_probability=probability)
    risk_by_tenure = risk_source.groupby("tenure_bucket", observed=True)["_probability"].mean()
    tenure_order = ["0-6 onboarding", "7-24 growth", "25-48 mature", "49+ loyal"]
    risk_by_tenure = risk_by_tenure.reindex(tenure_order).dropna()
    risk_axis.plot(
        risk_by_tenure.index,
        risk_by_tenure.values * 100,
        marker="o",
        color="#ea580c",
        linewidth=2.5,
    )
    risk_axis.set(
        title="Average predicted risk by lifecycle",
        ylabel="Average probability (%)",
        ylim=(0, max(100, max(risk_by_tenure.values * 120, default=100))),
    )
    risk_axis.tick_params(axis="x", rotation=25, labelsize=8)
    _style_axis(risk_axis)

    opportunity_axis = figure.add_subplot(grid[2, :7])
    opportunity = (
        risk_source.groupby(["Contract", "InternetService"], observed=True)
        .agg(
            customers=("customerID", "nunique"),
            average_probability=("_probability", "mean"),
            mrr_at_risk=("MonthlyCharges", lambda values: 0.0),
        )
        .reset_index()
    )
    opportunity["mrr_at_risk"] = (
        risk_source.groupby(["Contract", "InternetService"], observed=True)
        .apply(lambda group: (group["MonthlyCharges"] * group["_probability"].fillna(0)).sum())
        .to_numpy()
    )
    opportunity = opportunity.nlargest(6, "mrr_at_risk").sort_values("mrr_at_risk")
    labels = opportunity["Contract"] + " · " + opportunity["InternetService"]
    opportunity_axis.barh(labels, opportunity["mrr_at_risk"], color="#0f766e")
    opportunity_axis.set(
        title="Highest probability-weighted MRR exposure",
        xlabel="Monthly revenue at risk (estimate)",
    )
    opportunity_axis.xaxis.set_major_formatter(lambda value, _: f"${value / 1_000:.0f}K")
    _style_axis(opportunity_axis)

    note_axis = figure.add_subplot(grid[2, 7:])
    note_axis.axis("off")
    note_axis.text(
        0.02,
        0.92,
        "Retention interpretation",
        fontsize=14,
        fontweight="bold",
        color="#0f172a",
        transform=note_axis.transAxes,
    )
    note_axis.text(
        0.02,
        0.67,
        "Use predicted risk to prioritize human review,\n"
        "not automatic retention decisions.",
        fontsize=8.5,
        color="#334155",
        linespacing=1.5,
        transform=note_axis.transAxes,
    )
    note_axis.text(
        0.02,
        0.42,
        "Validate retention actions with experiments;\n"
        "segment associations are not causal.",
        fontsize=8.5,
        color="#475569",
        linespacing=1.7,
        transform=note_axis.transAxes,
    )
    note_axis.text(
        0.02,
        0.14,
        "• Churn is historical observed outcome\n"
        "• Probabilities are out-of-fold model scores\n"
        "• Revenue and support measures are directional proxies",
        fontsize=7.5,
        color="#64748b",
        linespacing=1.5,
        transform=note_axis.transAxes,
    )

    figure.savefig(path, dpi=160, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)
    return path


def _style_axis(axis: plt.Axes) -> None:
    """Apply the muted visual language used across preview components."""
    axis.set_facecolor("white")
    axis.spines[["top", "right"]].set_visible(False)
    axis.grid(axis="x", alpha=0.2)
    axis.title.set_fontsize(11)
    axis.title.set_fontweight("bold")
