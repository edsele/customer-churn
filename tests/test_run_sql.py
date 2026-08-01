"""Tests for SQL runner failure signaling."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import run_sql


def test_run_all_queries_returns_failure_count(tmp_path: Path, monkeypatch) -> None:
    """A failed SQL asset must make the command-line runner fail."""
    (tmp_path / "01_valid.sql").write_text("SELECT 1 AS value;", encoding="utf-8")
    (tmp_path / "02_invalid.sql").write_text("INVALID SQL;", encoding="utf-8")

    def fake_execute_query(query: str) -> pd.DataFrame:
        if "INVALID" in query:
            raise ValueError("invalid query")
        return pd.DataFrame({"value": [1]})

    monkeypatch.setattr(run_sql, "execute_query", fake_execute_query)

    assert run_sql.run_all_queries(tmp_path) == 1


def test_resolve_query_file_accepts_repository_sql_asset() -> None:
    path = run_sql.resolve_query_file("01_churn_by_segment.sql")

    assert path.parent == run_sql.resolve_path("sql").resolve()
    assert path.name == "01_churn_by_segment.sql"


@pytest.mark.parametrize(
    "query_name",
    ["../run_pipeline.py", "sql/01_churn_by_segment.sql", "01_churn_by_segment.txt"],
)
def test_resolve_query_file_rejects_paths_and_non_sql_assets(query_name: str) -> None:
    with pytest.raises(ValueError, match="repository sql directory"):
        run_sql.resolve_query_file(query_name)


def test_main_rejects_unsafe_query_before_execution(monkeypatch) -> None:
    executed_queries: list[str] = []
    monkeypatch.setattr(run_sql, "setup_logging", lambda: None)
    monkeypatch.setattr(
        run_sql,
        "execute_query",
        lambda query: executed_queries.append(query),
    )

    assert run_sql.main(["--query", "../run_pipeline.py"]) == 1
    assert executed_queries == []
