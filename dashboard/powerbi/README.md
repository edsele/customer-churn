# Power BI Dashboard

[`Customer_Churn_Analytics.pbix`](Customer_Churn_Analytics.pbix) is a native,
interactive Power BI Desktop report for the customer-churn project. It embeds
the observed-source snapshot used at build time, so it opens without an
immediate refresh. The refreshable customer-level source is generated at
`dashboard/powerbi/data/customer_churn_observed_dashboard.csv` by the pipeline
and is kept out of version control as a rebuildable artifact.

## Included executive page

The report is scoped to the 7,043 independently observed IBM Telco customer
records. It deliberately excludes the project's lineage-labeled 21K prototype
scenario from executive metrics.

The page contains:

- Customer count, observed churn rate, monthly revenue proxy, probability-weighted
  revenue at risk, high-risk customer count, average predicted risk, and
  average remaining-revenue proxy.
- Observed churn by contract, a predicted-risk-band distribution, and revenue
  at risk by contract.
- Interactive Contract and Internet Service slicers that filter the KPI block
  and every supporting visual.

After a full pipeline run and Power BI refresh, reconcile the unfiltered KPI
values before sharing the report. Use
[`13_scoring_coverage_and_value_at_risk.sql`](../../sql/13_scoring_coverage_and_value_at_risk.sql)
for exposure and high-risk-count checks, and
[`14_retention_snapshot.sql`](../../sql/14_retention_snapshot.sql) for customer
count and observed-churn checks. The run manifest supplies model provenance.

## Metric guardrails

| Metric | Definition | Reporting note |
|---|---|---|
| Observed churn rate | Churned observed customers / observed customers | Historical outcome, not a forecast. |
| Monthly revenue proxy | Sum of `MonthlyCharges` | Snapshot MRR proxy; not a finance ledger or monthly time series. |
| Revenue at risk | Sum of `MonthlyCharges × predicted churn probability` | Model-estimated probability-weighted monthly exposure, not booked loss. |
| High-risk customers | Probability at or above the model decision threshold (0.50) | A review queue signal, not an automatic retention decision. |
| Remaining-revenue proxy | Average documented 72-month-horizon estimate | A planning proxy, not approved customer lifetime value. |

See [`DAX_MEASURES.md`](DAX_MEASURES.md) for the report measure definitions.

## Open and refresh

1. Run `python run_pipeline.py` from the repository root to regenerate the
   observed scored export.
2. Open `Customer_Churn_Analytics.pbix` in Power BI Desktop.
3. To refresh from a newly generated local CSV, use **Transform data → Data
   source settings** and point the existing connection to
   `dashboard/powerbi/data/customer_churn_observed_dashboard.csv` in your clone.
4. Refresh, validate the default KPI values with the SQL checks above, rename
   the page **Executive Summary** if it retains a default name, and save.

The source has one row per customer, a non-null unique `customerID`, an
observed historical churn label, and an out-of-fold model probability. The
pipeline creates it with `export_powerbi_dataset`, which filters on
`record_source = observed` before writing the report source.

## Executive-report walkthrough

For stakeholder review, the report supports a concise narrative:

1. Start with the observed churn rate and probability-weighted MRR exposure.
2. Use the contract chart to identify whether risk is concentrated in
   month-to-month relationships.
3. Use the risk distribution to size the outreach queue, then filter by
   Contract and Internet Service to define a retention cohort.
4. Treat model probability as prioritization evidence and confirm outcomes
   through an experiment or controlled retention program.
