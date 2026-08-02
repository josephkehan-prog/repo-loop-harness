"""Reproducible proof report for RepoLoop's implemented repository contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_loop.discovery import compile_capsule, discover_repository


def verify_repository_contract(path: str | Path) -> dict[str, Any]:
    """Verify deterministic discovery and fail-closed capsule defaults."""
    first_snapshot = discover_repository(path)
    second_snapshot = discover_repository(path)
    capsule = compile_capsule(first_snapshot)
    checks = [
        _check("snapshot_repeatable", first_snapshot == second_snapshot),
        _check(
            "evidence_paths_portable",
            all(
                not Path(item["path"]).is_absolute()
                for item in first_snapshot["evidence"]
            ),
        ),
        _check("trust_quarantined", capsule["trust"] == "quarantined"),
        _check(
            "destructive_actions_denied",
            capsule["permissions"]["destructive"] == "deny",
        ),
        _check(
            "external_writes_gated",
            capsule["permissions"]["external_write"] == "approval",
        ),
    ]
    passed = sum(1 for check in checks if check["passed"])
    failed = len(checks) - passed
    return {
        "schema_version": 1,
        "result": "pass" if failed == 0 else "fail",
        "repository": first_snapshot["repository"],
        "snapshot_digest": first_snapshot["fact_digest"],
        "completion_checks": capsule["verification"]["completion_requires"],
        "checks": checks,
        "summary": {"passed": passed, "failed": failed},
    }


def _check(name: str, passed: bool) -> dict[str, str | bool]:
    return {"name": name, "passed": passed}
