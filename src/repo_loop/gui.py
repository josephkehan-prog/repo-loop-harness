"""Loopback-only browser workbench for repository capsule inspection."""

from __future__ import annotations

import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from repo_loop.discovery import compile_capsule, discover_repository

LOOPBACK_HOST = "127.0.0.1"
ASSET_TYPES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.css": ("app.css", "text/css; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
}
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "base-uri 'none'; "
    "font-src 'self'; "
    "object-src 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'none'"
)


def dashboard_payload(
    repository: str | Path, *, backend_configured: bool
) -> dict[str, Any]:
    """Build a fresh browser-safe projection from deterministic scanner output."""
    snapshot = discover_repository(repository)
    capsule = compile_capsule(snapshot)
    return {
        "repository": dict(snapshot["repository"]),
        "stack": {
            "languages": list(snapshot["stack"]["languages"]),
            "package_managers": list(snapshot["stack"]["package_managers"]),
        },
        "commands": [
            {"name": name, "command": command}
            for name, command in sorted(snapshot["commands"].items())
        ],
        "evidence": [dict(item) for item in snapshot["evidence"]],
        "digest": snapshot["fact_digest"],
        "capsule": {
            "id": capsule["repo_id"],
            "trust": capsule["trust"],
            "verification": dict(capsule["verification"]),
            "loop": dict(capsule["loop"]),
            "permissions": dict(capsule["permissions"]),
        },
        "runtime": {
            "state": "backend configured"
            if backend_configured
            else "backend not configured"
        },
    }


class RepoLoopGuiServer(ThreadingHTTPServer):
    """HTTP server carrying the fixed repository and runtime state."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        *,
        repository: Path,
        backend_configured: bool,
        assets: dict[str, tuple[bytes, str]],
    ) -> None:
        self.repository = repository
        self.backend_configured = backend_configured
        self.assets = assets
        super().__init__(server_address, handler)


class RepoLoopGuiHandler(BaseHTTPRequestHandler):
    """Serve a small route allowlist; repository paths never become HTTP routes."""

    server: RepoLoopGuiServer
    server_version = "RepoLoopGUI"
    sys_version = ""

    def do_GET(self) -> None:
        expected_hosts = {
            LOOPBACK_HOST,
            f"{LOOPBACK_HOST}:{self.server.server_port}",
        }
        if self.headers.get("Host", "") not in expected_hosts:
            self._send_json(
                {"error": "invalid host"},
                status=HTTPStatus.MISDIRECTED_REQUEST,
            )
            return
        if self.headers.get("Sec-Fetch-Site") not in (None, "none", "same-origin"):
            self._send_json(
                {"error": "cross-site request denied"},
                status=HTTPStatus.FORBIDDEN,
            )
            return
        route = urlsplit(self.path).path
        if route == "/api/health":
            self._send_json({"status": "ok"})
            return
        if route == "/api/dashboard":
            try:
                payload = dashboard_payload(
                    self.server.repository,
                    backend_configured=self.server.backend_configured,
                )
            except (OSError, ValueError):
                self._send_json(
                    {"error": "repository scan failed"},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return
            self._send_json(payload)
            return
        asset = self.server.assets.get(route)
        if asset is not None:
            body, content_type = asset
            self._send(body, content_type=content_type)
            return
        self._send_json({"error": "not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_json(
        self, payload: dict[str, Any], *, status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self._send(body, content_type="application/json; charset=utf-8", status=status)

    def _send(
        self,
        body: bytes,
        *,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.end_headers()
        self.wfile.write(body)


def create_gui_server(
    repository: str | Path,
    *,
    port: int = 0,
    backend_configured: bool = False,
) -> RepoLoopGuiServer:
    """Create a fixed-loopback server after validating the repository path."""
    resolved_repository = Path(repository).expanduser().resolve()
    discover_repository(resolved_repository)
    web_root = files("repo_loop").joinpath("web")
    assets = {
        route: (web_root.joinpath(filename).read_bytes(), content_type)
        for route, (filename, content_type) in ASSET_TYPES.items()
    }
    return RepoLoopGuiServer(
        (LOOPBACK_HOST, port),
        RepoLoopGuiHandler,
        repository=resolved_repository,
        backend_configured=backend_configured,
        assets=assets,
    )


def serve_gui(
    repository: str | Path,
    *,
    port: int = 0,
    open_browser: bool = True,
    backend_configured: bool = False,
) -> None:
    """Serve the workbench until interrupted, opening the browser when requested."""
    server = create_gui_server(
        repository,
        port=port,
        backend_configured=backend_configured,
    )
    url = f"http://{LOOPBACK_HOST}:{server.server_port}/"
    print(f"Repository workbench: {url}", flush=True)
    print("Press Ctrl-C to stop.", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
