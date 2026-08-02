from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from repo_loop.gui import create_gui_server, dashboard_payload


class DashboardPayloadTests(unittest.TestCase):
    def test_payload_projects_repository_facts_and_governance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "pyproject.toml").write_text(
                "[project]\nname = 'sample'\n", encoding="utf-8"
            )

            payload = dashboard_payload(repository, backend_configured=False)

        self.assertEqual(payload["repository"]["name"], repository.name)
        self.assertIn("python", payload["stack"]["languages"])
        self.assertEqual(payload["capsule"]["trust"], "quarantined")
        self.assertEqual(payload["runtime"]["state"], "backend not configured")
        self.assertEqual(len(payload["digest"]), 64)


class GuiServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.repository = Path(self.temporary_directory.name)
        (self.repository / "pyproject.toml").write_text(
            "[project]\nname = 'sample'\n", encoding="utf-8"
        )
        self.server = create_gui_server(self.repository, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = f"http://{host}:{port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary_directory.cleanup()

    def fetch(self, path: str = "/"):
        return urllib.request.urlopen(f"{self.base_url}{path}", timeout=2)

    def test_server_is_loopback_only_and_exposes_health(self) -> None:
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

        with self.fetch("/api/health") as response:
            payload = json.load(response)

        self.assertEqual(payload, {"status": "ok"})

    def test_dashboard_api_returns_fresh_read_only_projection(self) -> None:
        with self.fetch("/api/dashboard") as response:
            payload = json.load(response)
            headers = response.headers

        self.assertEqual(payload["repository"]["path"], str(self.repository.resolve()))
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertIsNone(headers["Access-Control-Allow-Origin"])

    def test_index_is_semantic_local_app_with_security_headers(self) -> None:
        with self.fetch() as response:
            html = response.read().decode("utf-8")
            headers = response.headers

        self.assertIn('data-testid="repository-name"', html)
        self.assertIn("Refresh repository", html)
        self.assertIn("Evidence ledger", html)
        self.assertIn("Policy boundary", html)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def test_static_assets_are_packaged_and_javascript_is_local(self) -> None:
        with self.fetch("/app.css") as response:
            self.assertIn("text/css", response.headers["Content-Type"])
            self.assertIn("capsule-spine", response.read().decode("utf-8"))
        with self.fetch("/app.js") as response:
            javascript = response.read().decode("utf-8")
            self.assertIn("/api/dashboard", javascript)
            self.assertNotIn("https://", javascript)

    def test_unknown_and_traversal_routes_are_not_served(self) -> None:
        for path in ("/missing", "/../pyproject.toml", "/%2e%2e/pyproject.toml"):
            with self.subTest(path=path), self.assertRaises(urllib.error.HTTPError) as error:
                self.fetch(path)
            self.assertEqual(error.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
