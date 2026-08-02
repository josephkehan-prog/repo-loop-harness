"""Textual dashboard for repository facts and capsule policy."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static, TabbedContent, TabPane

from repo_loop.discovery import compile_capsule, discover_repository
from repo_loop.presentation import terminal_text

Snapshot = dict[str, Any]
Capsule = dict[str, Any]
Loader = Callable[[Path], tuple[Snapshot, Capsule]]


def build_dashboard_model(
    snapshot: Snapshot,
    capsule: Capsule,
    *,
    backend_configured: bool,
) -> dict[str, Any]:
    """Project immutable discovery facts into display-ready values."""
    repository = snapshot["repository"]
    dirty_paths = list(repository["dirty_paths"])
    repository_state = "clean"
    if repository["dirty"]:
        repository_state = f"dirty ({len(dirty_paths)} paths)"
    branch = repository["branch"] or "detached or unversioned"
    head = repository["head"][:12] if repository["head"] else "unversioned"
    return {
        "repository_name": terminal_text(repository["name"]),
        "repository_path": terminal_text(repository["path"]),
        "repository_state": repository_state,
        "branch": terminal_text(branch),
        "head": terminal_text(head),
        "languages": [terminal_text(item) for item in snapshot["stack"]["languages"]],
        "package_managers": [
            terminal_text(item) for item in snapshot["stack"]["package_managers"]
        ],
        "commands": sorted(
            (terminal_text(name), terminal_text(command))
            for name, command in snapshot["commands"].items()
        ),
        "evidence": sorted(
            (terminal_text(item["fact"]), terminal_text(item["path"]))
            for item in snapshot["evidence"]
        ),
        "digest": snapshot["fact_digest"],
        "repo_id": capsule["repo_id"],
        "trust": capsule["trust"],
        "completion_requires": list(capsule["verification"]["completion_requires"]),
        "loop": dict(capsule["loop"]),
        "permissions": dict(capsule["permissions"]),
        "runtime_state": "backend configured"
        if backend_configured
        else "backend not configured",
    }


class RepoLoopApp(App[None]):
    """Read-only repository and capsule dashboard."""

    TITLE = "Repository Loop Agent Harness"
    SUB_TITLE = "governed repository capsule"
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]
    CSS = """
    Screen {
        background: #0b1020;
        color: #d8e2ff;
    }

    #shell {
        padding: 1 2;
    }

    #hero {
        height: 5;
        border: tall #6177a8;
        background: #111a31;
        padding: 0 2;
    }

    #repo-name {
        width: 2fr;
        text-style: bold;
        color: #8bd5ca;
        content-align: left middle;
    }

    #repo-meta {
        width: 3fr;
        color: #b8c0e0;
        content-align: left middle;
    }

    #runtime-state {
        width: 2fr;
        color: #eed49f;
        content-align: right middle;
    }

    TabbedContent {
        height: 1fr;
        margin-top: 1;
    }

    TabPane {
        padding: 1 2;
    }

    #overview-copy, #policy-copy {
        padding: 1;
    }

    DataTable {
        height: 1fr;
    }
    """

    def __init__(
        self,
        repository: str | Path,
        *,
        loader: Loader | None = None,
        backend_configured: bool = False,
    ) -> None:
        super().__init__()
        self.repository = Path(repository).expanduser().resolve()
        self.loader = loader or self._default_loader
        self.backend_configured = backend_configured
        self.refresh_count = 0
        self.model = self._load_model()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="shell"):
            with Horizontal(id="hero"):
                yield Static(
                    self.model["repository_name"], id="repo-name", markup=False
                )
                yield Static(self._repository_meta(), id="repo-meta", markup=False)
                yield Static(
                    self.model["runtime_state"], id="runtime-state", markup=False
                )
            with TabbedContent(initial="overview"):
                with TabPane("Overview", id="overview"):
                    yield Static(
                        self._overview_text(), id="overview-copy", markup=False
                    )
                with TabPane("Commands", id="commands"):
                    yield DataTable(id="commands-table")
                with TabPane("Evidence", id="evidence"):
                    yield DataTable(id="evidence-table")
                with TabPane("Policy", id="policy"):
                    yield Static(self._policy_text(), id="policy-copy", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        self._populate_tables()

    def action_refresh(self) -> None:
        self.model = self._load_model()
        self.refresh_count += 1
        self.query_one("#repo-name", Static).update(self.model["repository_name"])
        self.query_one("#repo-meta", Static).update(self._repository_meta())
        self.query_one("#runtime-state", Static).update(self.model["runtime_state"])
        self.query_one("#overview-copy", Static).update(self._overview_text())
        self.query_one("#policy-copy", Static).update(self._policy_text())
        self._populate_tables()
        self.notify("Repository facts refreshed", timeout=1.5)

    def _load_model(self) -> dict[str, Any]:
        snapshot, capsule = self.loader(self.repository)
        return build_dashboard_model(
            snapshot,
            capsule,
            backend_configured=self.backend_configured,
        )

    @staticmethod
    def _default_loader(repository: Path) -> tuple[Snapshot, Capsule]:
        snapshot = discover_repository(repository)
        return snapshot, compile_capsule(snapshot)

    def _repository_meta(self) -> str:
        return (
            f"{self.model['branch']} @ {self.model['head']}\n"
            f"{self.model['repository_state']} · {self.model['repository_path']}"
        )

    def _overview_text(self) -> str:
        languages = ", ".join(self.model["languages"]) or "none detected"
        managers = ", ".join(self.model["package_managers"]) or "none detected"
        return (
            f"Capsule       {self.model['repo_id']}\n"
            f"Trust         {self.model['trust']}\n"
            f"Languages     {languages}\n"
            f"Package tools {managers}\n"
            f"Fact digest   {self.model['digest']}"
        )

    def _policy_text(self) -> str:
        required = ", ".join(self.model["completion_requires"]) or "none discovered"
        permissions = self.model["permissions"]
        loop = self.model["loop"]
        return (
            f"Completion checks   {required}\n"
            f"External writes     {permissions['external_write']}\n"
            f"Destructive actions {permissions['destructive']}\n"
            f"Secrets             {permissions['secrets']}\n"
            f"Iteration ceiling   {loop['max_iterations']}\n"
            f"Attempts per item   {loop['max_attempts_per_item']}\n"
            f"Stall limit         {loop['stall_limit']}"
        )

    def _populate_tables(self) -> None:
        commands = self.query_one("#commands-table", DataTable)
        evidence = self.query_one("#evidence-table", DataTable)
        if not commands.columns:
            commands.add_columns("Capability", "Command")
        if not evidence.columns:
            evidence.add_columns("Fact", "Evidence path")
        commands.clear(columns=False)
        evidence.clear(columns=False)
        command_rows = self.model["commands"] or [("—", "No commands discovered")]
        evidence_rows = self.model["evidence"] or [
            ("—", "No stack evidence discovered")
        ]
        commands.add_rows(command_rows)
        evidence.add_rows(evidence_rows)


def run_tui(repository: str | Path) -> None:
    RepoLoopApp(repository).run()
