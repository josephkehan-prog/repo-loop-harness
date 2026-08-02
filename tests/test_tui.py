from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from textual.widgets import Static

from repo_loop.discovery import compile_capsule, discover_repository
from repo_loop.tui import RepoLoopApp, build_dashboard_model


class DashboardModelTests(unittest.TestCase):
    def test_model_projects_snapshot_and_policy_without_mutating_inputs(self) -> None:
        snapshot = {
            "schema_version": 1,
            "repository": {
                "name": "sample",
                "path": "/tmp/sample",
                "branch": "main",
                "head": "abc123",
                "dirty": False,
                "dirty_paths": [],
            },
            "stack": {"languages": ["python"], "package_managers": ["uv"]},
            "commands": {"test": "uv run pytest"},
            "evidence": [{"fact": "language:python", "path": "pyproject.toml"}],
            "fact_digest": "d" * 64,
        }
        capsule = {
            "repo_id": "sample-dddddddddddd",
            "trust": "quarantined",
            "verification": {"completion_requires": ["test"]},
            "loop": {"max_iterations": 12, "stall_limit": 3},
            "permissions": {"external_write": "approval", "destructive": "deny"},
        }
        original_snapshot = json.dumps(snapshot, sort_keys=True)
        original_capsule = json.dumps(capsule, sort_keys=True)

        model = build_dashboard_model(snapshot, capsule, backend_configured=False)

        self.assertEqual(model["repository_name"], "sample")
        self.assertEqual(model["repository_state"], "clean")
        self.assertEqual(model["runtime_state"], "backend not configured")
        self.assertEqual(model["commands"], [("test", "uv run pytest")])
        self.assertEqual(model["evidence"], [("language:python", "pyproject.toml")])
        self.assertEqual(json.dumps(snapshot, sort_keys=True), original_snapshot)
        self.assertEqual(json.dumps(capsule, sort_keys=True), original_capsule)

    def test_model_surfaces_dirty_state_and_configured_backend(self) -> None:
        snapshot = {
            "repository": {
                "name": "dirty-repo",
                "path": "/tmp/dirty-repo",
                "branch": None,
                "head": None,
                "dirty": True,
                "dirty_paths": ["a.py", "b.py"],
            },
            "stack": {"languages": [], "package_managers": []},
            "commands": {},
            "evidence": [],
            "fact_digest": "a" * 64,
        }
        capsule = {
            "repo_id": "dirty-repo-aaaaaaaaaaaa",
            "trust": "quarantined",
            "verification": {"completion_requires": []},
            "loop": {"max_iterations": 12, "stall_limit": 3},
            "permissions": {"external_write": "approval", "destructive": "deny"},
        }

        model = build_dashboard_model(snapshot, capsule, backend_configured=True)

        self.assertEqual(model["repository_state"], "dirty (2 paths)")
        self.assertEqual(model["runtime_state"], "backend configured")
        self.assertEqual(model["branch"], "detached or unversioned")


class RepoLoopAppTests(unittest.IsolatedAsyncioTestCase):
    async def test_app_boots_with_repository_facts_and_keyboard_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "pyproject.toml").write_text(
                "[tool.ruff]\nline-length = 100\n", encoding="utf-8"
            )
            app = RepoLoopApp(repository)

            async with app.run_test(size=(120, 40)) as pilot:
                title = app.query_one("#repo-name", Static)
                runtime = app.query_one("#runtime-state", Static)
                self.assertIn(repository.name, str(title.renderable))
                self.assertIn("backend not configured", str(runtime.renderable))

                before = app.refresh_count
                await pilot.press("r")
                await pilot.pause()
                self.assertEqual(app.refresh_count, before + 1)

    async def test_app_uses_injected_discovery_for_repeatable_refresh(self) -> None:
        calls: list[Path] = []

        def discover(path: Path):
            calls.append(path)
            snapshot = discover_repository(path)
            return snapshot, compile_capsule(snapshot)

        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            app = RepoLoopApp(repository, loader=discover)

            async with app.run_test(size=(100, 32)) as pilot:
                await pilot.press("r")
                await pilot.pause()

        self.assertEqual(calls, [repository.resolve(), repository.resolve()])


if __name__ == "__main__":
    unittest.main()
