from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repo_loop.discovery import compile_capsule, discover_repository


class DiscoveryTests(unittest.TestCase):
    def make_repository(self, root: Path) -> None:
        subprocess.run(
            ["git", "init", "--initial-branch=main", str(root)],
            check=True,
            capture_output=True,
            text=True,
        )
        (root / "src").mkdir()
        (root / "src" / "demo.py").write_text("print('hello')\n", encoding="utf-8")
        (root / "package.json").write_text(
            json.dumps({"scripts": {"test": "node --test", "lint": "eslint ."}}),
            encoding="utf-8",
        )
        (root / "package-lock.json").write_text("{}\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "-c",
                "user.name=Test User",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-m",
                "fixture",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_discovers_versioned_repository_facts_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            self.make_repository(repository)

            first = discover_repository(repository)
            second = discover_repository(repository)

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], 1)
        self.assertEqual(first["repository"]["branch"], "main")
        self.assertFalse(first["repository"]["dirty"])
        self.assertIn("python", first["stack"]["languages"])
        self.assertIn("javascript", first["stack"]["languages"])
        self.assertEqual(first["stack"]["package_managers"], ["npm"])
        self.assertEqual(first["commands"]["test"], "npm test")
        self.assertEqual(first["commands"]["lint"], "npm run lint")
        self.assertEqual(len(first["fact_digest"]), 64)
        self.assertTrue(all(not Path(item["path"]).is_absolute() for item in first["evidence"]))

    def test_marks_dirty_paths_without_modifying_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            self.make_repository(repository)
            source = repository / "src" / "demo.py"
            source.write_text("print('changed')\n", encoding="utf-8")

            snapshot = discover_repository(repository)

            self.assertTrue(snapshot["repository"]["dirty"])
            self.assertEqual(snapshot["repository"]["dirty_paths"], ["src/demo.py"])
            self.assertEqual(source.read_text(encoding="utf-8"), "print('changed')\n")

    def test_compiles_governed_capsule_from_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            self.make_repository(repository)
            snapshot = discover_repository(repository)

        capsule = compile_capsule(snapshot)

        self.assertEqual(capsule["schema_version"], 1)
        self.assertEqual(capsule["trust"], "quarantined")
        self.assertEqual(capsule["snapshot_digest"], snapshot["fact_digest"])
        self.assertTrue(capsule["repo_id"].startswith(f"{snapshot['repository']['name']}-"))
        self.assertEqual(capsule["verification"]["completion_requires"], ["lint", "test"])
        self.assertEqual(capsule["permissions"]["external_write"], "approval")

    def test_rejects_missing_or_non_directory_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file_path = root / "file.txt"
            file_path.write_text("not a repository", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "does not exist"):
                discover_repository(root / "missing")
            with self.assertRaisesRegex(ValueError, "not a directory"):
                discover_repository(file_path)


if __name__ == "__main__":
    unittest.main()
