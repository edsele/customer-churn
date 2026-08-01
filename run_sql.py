"""SQL query runner for analytical scripts."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from src.config import resolve_path, setup_logging
from src.database import execute_query

logger = logging.getLogger(__name__)


def resolve_query_file(query_name: str) -> Path:
    """Return one repository SQL asset selected by a safe filename only."""
    requested_path = Path(query_name)
    if not query_name or requested_path.name != query_name or requested_path.suffix != ".sql":
        raise ValueError("--query must be a .sql filename in the repository sql directory.")

    directory = resolve_path("sql").resolve()
    query_path = (directory / requested_path).resolve()
    if query_path.parent != directory:
        raise ValueError("--query must be a .sql filename in the repository sql directory.")
    if not query_path.is_file():
        raise FileNotFoundError(f"SQL query file was not found: {requested_path.name}")
    return query_path


def run_all_queries(sql_dir: Path | None = None) -> int:
    """Execute all SQL query files, returning the number of failures."""
    directory = sql_dir or resolve_path("sql")
    query_files = sorted(directory.glob("*.sql"))
    query_files = [f for f in query_files if not f.name.startswith("00_")]
    failures = 0

    for script in query_files:
        sql = script.read_text(encoding="utf-8")
        print(f"\n{'=' * 60}")
        print(f"Query: {script.name}")
        print("=" * 60)
        try:
            result = execute_query(sql)
            print(result.to_string(index=False))
        except Exception as exc:
            failures += 1
            logger.error("Failed to run %s: %s", script.name, exc)
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run SQL analytics queries")
    parser.add_argument("--query", type=str, help="Specific SQL file name to run")
    args = parser.parse_args(argv)
    setup_logging()

    if args.query:
        try:
            path = resolve_query_file(args.query)
            result = execute_query(path.read_text(encoding="utf-8"))
            print(result.to_string(index=False))
        except (OSError, ValueError) as exc:
            logger.error("Failed to run query %s: %s", args.query, exc)
            return 1
        except Exception:
            logger.exception("Failed to run query %s", args.query)
            return 1
        return 0

    return int(run_all_queries() > 0)


if __name__ == "__main__":
    sys.exit(main())
