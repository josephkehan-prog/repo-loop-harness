from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repo_loop.proof import verify_repository_contract


class ProofTests(unittest.TestCase):
    def test_verifies_repository_contract_without_changing_git_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            subprocess.run(
                ["git", "init", "--initial-branch=main", str(repository)],
                check=True,
                capture_output=True,
                text=True,
            )
            source = repository / "example.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository),
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
            before = self.git_status(repository)

            report = verify_repository_contract(repository)
            after = self.git_status(repository)

            self.assertEqual(source.read_text(encoding="utf-8"), "VALUE = 1\n")

        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["summary"], {"passed": 5, "failed": 0})
        self.assertEqual(before, after)
        self.assertTrue(all(check["passed"] for check in report["checks"]))

    @staticmethod
    def git_status(repository: Path) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), "status", "--porcelain=v1"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout


if __name__ == "__main__":
    unittest.main()
