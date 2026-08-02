from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repo_loop.backend import BackendUnavailable, forward_to_backend
from repo_loop.cli import main
from repo_loop.presentation import terminal_text


class CliTests(unittest.TestCase):
    def invoke(self, arguments: list[str], environ: dict[str, str] | None = None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(arguments, environ={} if environ is None else environ)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_help_exposes_documented_command_groups(self) -> None:
        code, stdout, stderr = self.invoke(["--help"])

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("RepoLoop", stdout)
        for command in (
            "discover",
            "capsule",
            "proof",
            "tui",
            "gui",
            "run",
            "resume",
            "status",
        ):
            self.assertIn(command, stdout)

    def test_discover_prints_machine_readable_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, stdout, stderr = self.invoke(["discover", directory, "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["repository"]["path"], str(Path(directory).resolve()))
        self.assertEqual(payload["schema_version"], 1)

    def test_capsule_show_prints_compiled_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, stdout, stderr = self.invoke(["capsule", "show", directory, "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["trust"], "quarantined")
        self.assertIn("snapshot_digest", payload)

    def test_proof_prints_machine_readable_verification_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, stdout, stderr = self.invoke(["proof", directory, "--json"])

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(payload["result"], "pass")
        self.assertTrue(payload["checks"])
        self.assertTrue(all(check["passed"] for check in payload["checks"]))
        self.assertEqual(payload["summary"]["failed"], 0)

    def test_proof_prints_scannable_human_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, stdout, stderr = self.invoke(["proof", directory])

        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("Proof: PASS", stdout)
        self.assertIn("Snapshot repeatable", stdout)
        self.assertIn("Checks:", stdout)

    def test_invalid_repository_path_is_a_usage_error(self) -> None:
        code, stdout, stderr = self.invoke(["discover", "/definitely/missing/repo"])

        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("does not exist", stderr)

    def test_runtime_commands_fail_closed_without_backend(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, stdout, stderr = self.invoke(
                ["run", "understand", directory, "--mode", "discover"]
            )

        self.assertEqual(code, os.EX_UNAVAILABLE)
        self.assertEqual(stdout, "")
        self.assertIn("REPO_LOOP_BACKEND", stderr)
        self.assertIn("runtime backend is not configured", stderr)

    @patch("repo_loop.backend.subprocess.run")
    def test_backend_receives_arguments_without_shell_interpolation(self, run) -> None:
        run.return_value.returncode = 17

        code = forward_to_backend(
            ["status", "session with spaces"],
            {"REPO_LOOP_BACKEND": "python -m sample_backend"},
        )

        self.assertEqual(code, 17)
        run.assert_called_once_with(
            ["python", "-m", "sample_backend", "status", "session with spaces"],
            check=False,
        )

    def test_backend_rejects_missing_or_empty_configuration(self) -> None:
        with self.assertRaises(BackendUnavailable):
            forward_to_backend(["status", "abc"], {})
        with self.assertRaises(BackendUnavailable):
            forward_to_backend(["status", "abc"], {"REPO_LOOP_BACKEND": "   "})


class WrapperEndToEndTests(unittest.TestCase):
    def test_repository_wrapper_is_directly_executable(self) -> None:
        result = subprocess.run(
            [str(ROOT / "repo-loop"), "--version"],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "repo-loop 0.1.0")


class TerminalPresentationTests(unittest.TestCase):
    def test_control_characters_are_escaped_before_terminal_rendering(self) -> None:
        self.assertEqual(
            terminal_text("repo\x1b[31m\nname\t"),
            "repo\\x1b[31m\\x0aname\\x09",
        )


if __name__ == "__main__":
    unittest.main()
