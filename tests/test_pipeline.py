"""Tests for pipeline provenance capture and checksum normalization."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from src import __version__, pipeline


def test_sha256_file_normalizes_crlf_across_chunk_boundaries(tmp_path: Path) -> None:
    """Raw-data checksums should be stable across Git-managed line endings."""
    canonical_content = b"a" * 65_535 + b"\n001,No\n"
    windows_content = b"a" * 65_535 + b"\r\n001,No\r\n"
    unix_content = b"a" * 65_535 + b"\n001,No\n"
    windows_path = tmp_path / "windows.csv"
    unix_path = tmp_path / "unix.csv"
    windows_path.write_bytes(windows_content)
    unix_path.write_bytes(unix_content)

    expected = hashlib.sha256(canonical_content).hexdigest()

    assert pipeline._sha256_file(windows_path, normalize_crlf=True) == expected
    assert pipeline._sha256_file(unix_path, normalize_crlf=True) == expected
    assert pipeline._sha256_file(windows_path) != expected


def test_release_version_is_consistent_across_project_metadata() -> None:
    """Keep package, pipeline, and build metadata on the same release version."""
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE)

    assert match is not None
    assert match.group(1) == __version__
    assert pipeline.load_config()["project"]["version"] == __version__


def test_write_run_manifest_uses_pre_captured_context(
    tmp_path: Path, monkeypatch: object
) -> None:
    """Writing a manifest must not replace provenance captured before the run."""
    output_path = tmp_path / "run_manifest.json"
    context = {"git_dirty_before_run": False, "raw_data_sha256": "example"}

    def unexpected_context_build() -> dict[str, object]:
        raise AssertionError("run context should be supplied by the pipeline")

    monkeypatch.setattr(pipeline, "_build_run_context", unexpected_context_build)
    pipeline._write_run_manifest({"training": "skipped"}, output_path, run_context=context)

    manifest = json.loads(output_path.read_text(encoding="utf-8"))
    assert manifest["run_context"] == context


def test_smoke_run_captures_context_before_generated_outputs(
    tmp_path: Path, monkeypatch: object
) -> None:
    """The smoke path carries its initial context through to the manifest."""
    calls: list[str] = []
    captured_context: dict[str, object] | None = None
    featured = pd.DataFrame({"record_source": ["observed", "analytics_scenario"]})
    validation = SimpleNamespace(
        passed=True,
        observed_churn_rate=0.25,
        scenario_churn_rate=0.3,
    )
    config = {
        "project": {"name": "test-project", "version": "0.0.0"},
        "data": {"record_source_column": "record_source", "observed_label": "observed"},
    }
    expected_context = {"git_dirty_before_run": False, "raw_data_sha256": "example"}

    monkeypatch.setattr(pipeline, "load_config", lambda: config)
    monkeypatch.setattr(
        pipeline,
        "_build_run_context",
        lambda: calls.append("context") or expected_context,
    )
    monkeypatch.setattr(
        pipeline,
        "run_preprocessing_pipeline",
        lambda export: (calls.append("preprocessing") or (featured, validation)),
    )
    monkeypatch.setattr(
        pipeline,
        "run_feature_engineering",
        lambda data, export: calls.append("features") or data,
    )
    monkeypatch.setattr(pipeline, "run_eda", lambda data: calls.append("eda"))
    monkeypatch.setattr(pipeline, "resolve_path", lambda path: tmp_path / path)

    def capture_manifest(
        summary: dict[str, object],
        output_path: Path | None = None,
        run_context: dict[str, object] | None = None,
    ) -> None:
        nonlocal captured_context
        captured_context = run_context
        calls.append("manifest")

    monkeypatch.setattr(pipeline, "_write_run_manifest", capture_manifest)

    summary = pipeline.run_full_pipeline(skip_training=True)

    assert calls == ["context", "preprocessing", "features", "eda", "manifest"]
    assert captured_context == expected_context
    assert summary["training"] == "skipped"
