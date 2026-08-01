# Contributing

Thank you for improving Customer Churn & Behavioral Analytics.

## Local setup

Use Python 3.10 through 3.12 and install the verified dependency set:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install --require-hashes -r requirements.lock
python -m pre_commit install
```

To update the dependency lock, use the pinned lock-tool environment documented
in the README; do not hand-edit `requirements.lock`.

Before opening a pull request, run:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=src --cov-report=term-missing
python run_pipeline.py
python run_sql.py
```

## Contribution guidelines

- Keep source-data, synthetic-scenario, and model-evaluation scope explicit.
- Do not present proxy metrics as realized revenue, causal effects, or customer
  lifetime value.
- Add or update tests for behavior changes.
- Keep generated reports consistent with the committed source revision.
- Do not commit secrets, private customer data, local environments, or generated
  model artifacts that are excluded by `.gitignore`.

## Pull requests

Describe the problem, summarize the approach, note validation performed, and
call out any change to data scope, model evaluation, or dashboard metrics.
