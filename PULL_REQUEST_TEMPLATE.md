## Summary

Describe the problem and the change.

## Validation

- [ ] `python -m ruff check .`
- [ ] `python -m ruff format --check .`
- [ ] `python -m pytest --cov=src --cov-report=term-missing`
- [ ] `python run_pipeline.py` when pipeline behavior or generated evidence changed
- [ ] `python run_sql.py` when SQL or database behavior changed

## Data and reporting impact

- [ ] This change preserves the distinction between observed data and the synthetic scenario.
- [ ] I updated documentation, report artifacts, and dashboard guidance when metrics or definitions changed.
