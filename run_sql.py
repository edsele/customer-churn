"""SQL query runner for analytical scripts."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.config import resolve_path, setup_logging
from src.database import execute_query

logger = logging.getLogger(__name__)


def run_all_queries(sql_dir: Path | None = None) -> None:
    """Execute all SQL query files and print results."""
    directory = sql_dir or resolve_path("sql")
    query_files = sorted(directory.glob("*.sql"))
    query_files = [f for f in query_files if not f.name.startswith("00_")]

    for script in query_files:
        sql = script.read_text(encoding="utf-8")
        print(f"\n{'=' * 60}")
        print(f"Query: {script.name}")
        print("=" * 60)
        try:
            result = execute_query(sql)
            print(result.to_string(index=False))
        except Exception as exc:
            logger.error("Failed to run %s: %s", script.name, exc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SQL analytics queries")
    parser.add_argument("--query", type=str, help="Specific SQL file name to run")
    args = parser.parse_args(argv)
    setup_logging()

    if args.query:
        path = resolve_path(f"sql/{args.query}")
        result = execute_query(path.read_text(encoding="utf-8"))
        print(result.to_string(index=False))
    else:
        run_all_queries()
    return 0


if __name__ == "__main__":
    sys.exit(main())
