"""Tests for SQL runner failure signaling."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

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
