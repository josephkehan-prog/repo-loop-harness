"""Command-line wrapper for discovery, inspection, TUI, and runtime handoff."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

from repo_loop import __version__
from repo_loop.backend import BackendUnavailable, forward_to_backend
from repo_loop.discovery import compile_capsule, discover_repository
from repo_loop.presentation import terminal_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-loop",
        description="RepoLoop compiles repositories into governed agent capsules.",
    )
    parser.add_argument(
        "--version", action="version", version=f"repo-loop {__version__}"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    discover = commands.add_parser("discover", help="scan a repository read-only")
    discover.add_argument("path", type=Path)
    discover.add_argument("--json", action="store_true", help="emit JSON")

    capsule = commands.add_parser("capsule", help="inspect a compiled capsule")
    capsule_commands = capsule.add_subparsers(dest="capsule_command", required=True)
    capsule_show = capsule_commands.add_parser(
        "show", help="compile and show a capsule"
    )
    capsule_show.add_argument("path", type=Path)
    capsule_show.add_argument("--json", action="store_true", help="emit JSON")

    tui = commands.add_parser("tui", help="open the repository dashboard")
    tui.add_argument("path", type=Path, nargs="?", default=Path.cwd())

    gui = commands.add_parser("gui", help="open the local repository workbench")
    gui.add_argument("path", type=Path, nargs="?", default=Path.cwd())
    gui.add_argument(
        "--port",
        type=_port,
        default=0,
        help="loopback port (default: choose an available port)",
    )
    gui.add_argument(
        "--no-open",
        action="store_true",
        help="serve without opening the default browser",
    )

    run = commands.add_parser("run", help="hand a loop session to the runtime backend")
    run_commands = run.add_subparsers(dest="run_command", required=True)
    understand = run_commands.add_parser(
        "understand", help="run a repository understanding loop"
    )
    understand.add_argument("path", type=Path)
    understand.add_argument(
        "--mode", choices=("discover", "shadow"), default="discover"
    )
    repair = run_commands.add_parser("repair", help="run a bounded repair loop")
    repair.add_argument("path", type=Path)
    repair.add_argument("--issue", required=True)
    repair.add_argument("--mode", choices=("shadow",), default="shadow")

    resume = commands.add_parser("resume", help="resume an exact runtime checkpoint")
    resume.add_argument("session_id")
    status = commands.add_parser("status", help="inspect runtime status and evidence")
    status.add_argument("session_id")
    return parser


def main(
    arguments: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> int:
    raw_arguments = list(sys.argv[1:] if arguments is None else arguments)
    environment = os.environ if environ is None else environ
    parser = build_parser()
    try:
        parsed = parser.parse_args(raw_arguments)
    except SystemExit as error:
        return int(error.code)

    try:
        if parsed.command == "discover":
            return _show_snapshot(parsed.path, parsed.json)
        if parsed.command == "capsule":
            return _show_capsule(parsed.path, parsed.json)
        if parsed.command == "tui":
            return _run_tui(parsed.path, environment)
        if parsed.command == "gui":
            return _run_gui(
                parsed.path,
                port=parsed.port,
                open_browser=not parsed.no_open,
                environment=environment,
            )
        if parsed.command == "run":
            discover_repository(parsed.path)
        return forward_to_backend(raw_arguments, environment)
    except ValueError as error:
        print(f"repo-loop: error: {terminal_text(error)}", file=sys.stderr)
        return 2
    except BackendUnavailable as error:
        print(f"repo-loop: {error}", file=sys.stderr)
        return os.EX_UNAVAILABLE


def _show_snapshot(path: Path, as_json: bool) -> int:
    snapshot = discover_repository(path)
    if as_json:
        _print_json(snapshot)
        return 0
    repository = snapshot["repository"]
    print(f"Repository: {terminal_text(repository['name'])}")
    print(f"Path: {terminal_text(repository['path'])}")
    print(f"Revision: {terminal_text(repository['head'] or 'unversioned')}")
    print(f"State: {'dirty' if repository['dirty'] else 'clean'}")
    languages = ", ".join(snapshot["stack"]["languages"]) or "none detected"
    print(f"Languages: {terminal_text(languages)}")
    print(f"Digest: {snapshot['fact_digest']}")
    return 0


def _show_capsule(path: Path, as_json: bool) -> int:
    capsule = compile_capsule(discover_repository(path))
    if as_json:
        _print_json(capsule)
        return 0
    print(f"Capsule: {capsule['repo_id']}")
    print(f"Trust: {capsule['trust']}")
    print(
        f"Required checks: {', '.join(capsule['verification']['completion_requires']) or 'none'}"
    )
    print(f"External writes: {capsule['permissions']['external_write']}")
    return 0


def _run_tui(path: Path, environment: Mapping[str, str]) -> int:
    from repo_loop.tui import RepoLoopApp

    app = RepoLoopApp(
        path, backend_configured=bool(environment.get("REPO_LOOP_BACKEND", "").strip())
    )
    app.run()
    return 0


def _run_gui(
    path: Path,
    *,
    port: int,
    open_browser: bool,
    environment: Mapping[str, str],
) -> int:
    from repo_loop.gui import serve_gui

    serve_gui(
        path,
        port=port,
        open_browser=open_browser,
        backend_configured=bool(environment.get("REPO_LOOP_BACKEND", "").strip()),
    )
    return 0


def _port(value: str) -> int:
    port = int(value)
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535")
    return port


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
