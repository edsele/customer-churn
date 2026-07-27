"""Configuration loading and project path utilities."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load YAML configuration from disk."""
    path = config_path or CONFIG_PATH
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def resolve_path(relative_path: str) -> Path:
    """Resolve a project-relative path to an absolute path."""
    return PROJECT_ROOT / relative_path


def setup_logging(level: str = "INFO", log_format: str | None = None) -> None:
    """Configure root logging for pipeline scripts."""
    config = load_config()
    fmt = log_format or config.get("logging", {}).get(
        "format", "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger."""
    return logging.getLogger(name)
