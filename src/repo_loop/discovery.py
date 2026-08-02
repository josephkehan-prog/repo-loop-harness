"""Deterministic, read-only repository discovery and capsule compilation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

IGNORED_DIRECTORIES = frozenset(
    {
        ".git",
        ".hg",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".svn",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
        "venv",
    }
)

LANGUAGE_EXTENSIONS = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".go": "go",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".lua": "lua",
    ".php": "php",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".swift": "swift",
    ".ts": "typescript",
    ".tsx": "typescript",
}

PACKAGE_MARKERS = {
    "bun": ("bun.lock", "bun.lockb"),
    "cargo": ("Cargo.lock", "Cargo.toml"),
    "go": ("go.mod",),
    "npm": ("package-lock.json", "package.json"),
    "pnpm": ("pnpm-lock.yaml",),
    "poetry": ("poetry.lock",),
    "uv": ("uv.lock",),
    "yarn": ("yarn.lock",),
}

COMMAND_NAMES = ("build", "format", "lint", "security", "test", "typecheck")


def discover_repository(path: str | Path) -> dict[str, Any]:
    """Return a deterministic snapshot without writing to the target repository."""
    repository = Path(path).expanduser().resolve()
    _validate_repository_path(repository)
    files = _repository_files(repository)
    git = _git_facts(repository)
    stack, stack_evidence = _stack_facts(repository, files)
    commands, command_evidence = _command_facts(repository, files, stack)
    evidence = sorted(
        [*stack_evidence, *command_evidence],
        key=lambda item: (item["fact"], item["path"]),
    )

    repository_facts = {
        "name": repository.name,
        "path": str(repository),
        **git,
    }
    digest_payload = {
        "repository": {
            key: value for key, value in repository_facts.items() if key != "path"
        },
        "stack": stack,
        "commands": commands,
        "evidence": evidence,
    }
    return {
        "schema_version": 1,
        "repository": repository_facts,
        "stack": stack,
        "commands": commands,
        "evidence": evidence,
        "fact_digest": _digest(digest_payload),
    }


def compile_capsule(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Compile snapshot facts into a fail-closed, portable policy contract."""
    repository = dict(snapshot["repository"])
    stack = {
        "languages": list(snapshot["stack"]["languages"]),
        "package_managers": list(snapshot["stack"]["package_managers"]),
    }
    commands = dict(snapshot["commands"])
    digest = str(snapshot["fact_digest"])
    repo_slug = re.sub(r"[^a-z0-9]+", "-", repository["name"].lower()).strip("-")
    return {
        "schema_version": 1,
        "repo_id": f"{repo_slug or 'repository'}-{digest[:12]}",
        "snapshot_digest": digest,
        "trust": "quarantined",
        "repository": repository,
        "stack": stack,
        "commands": commands,
        "verification": {"completion_requires": sorted(commands)},
        "loop": {
            "max_iterations": 12,
            "max_attempts_per_item": 3,
            "stall_limit": 3,
        },
        "permissions": {
            "external_write": "approval",
            "destructive": "deny",
            "secrets": "vault-only",
        },
    }


def _validate_repository_path(repository: Path) -> None:
    if not repository.exists():
        raise ValueError(f"repository path does not exist: {repository}")
    if not repository.is_dir():
        raise ValueError(f"repository path is not a directory: {repository}")


def _repository_files(repository: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, directories, filenames in os.walk(repository, followlinks=False):
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in IGNORED_DIRECTORIES
        )
        root = Path(current_root)
        for filename in sorted(filenames):
            candidate = root / filename
            if not candidate.is_symlink():
                files.append(candidate.relative_to(repository))
    return sorted(files, key=lambda item: item.as_posix())


def _git_facts(repository: Path) -> dict[str, Any]:
    head = _git(repository, "rev-parse", "HEAD")
    if head is None:
        return {
            "is_git_repository": False,
            "head": None,
            "branch": None,
            "dirty": False,
            "dirty_paths": [],
        }

    branch = _git(repository, "symbolic-ref", "--quiet", "--short", "HEAD")
    status = _git_raw(repository, "status", "--porcelain=v1", "-z") or ""
    dirty_paths = _porcelain_paths(status)
    return {
        "is_git_repository": True,
        "head": head,
        "branch": branch,
        "dirty": bool(dirty_paths),
        "dirty_paths": dirty_paths,
    }


def _git(repository: Path, *arguments: str) -> str | None:
    output = _git_raw(repository, *arguments)
    return output.strip() if output is not None else None


def _git_raw(repository: Path, *arguments: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _porcelain_paths(status: str) -> list[str]:
    records = [record for record in status.split("\0") if record]
    paths: list[str] = []
    index = 0
    while index < len(records):
        record = records[index]
        path = record[3:] if len(record) > 3 else record
        if record[:2].strip() in {"R", "C"} and index + 1 < len(records):
            index += 1
            path = records[index]
        paths.append(path)
        index += 1
    return sorted(set(paths))


def _stack_facts(
    repository: Path, files: list[Path]
) -> tuple[dict[str, list[str]], list[dict[str, str]]]:
    language_paths: dict[str, str] = {}
    file_names = {file.as_posix() for file in files}
    for file in files:
        language = LANGUAGE_EXTENSIONS.get(file.suffix.lower())
        if language and language not in language_paths:
            language_paths[language] = file.as_posix()
    if "package.json" in file_names and "javascript" not in language_paths:
        language_paths["javascript"] = "package.json"

    managers: list[str] = []
    manager_paths: dict[str, str] = {}
    for manager, markers in PACKAGE_MARKERS.items():
        for marker in markers:
            if marker in file_names:
                managers.append(manager)
                manager_paths[manager] = marker
                break

    evidence = [
        {"fact": f"language:{language}", "path": path}
        for language, path in sorted(language_paths.items())
    ]
    evidence.extend(
        {"fact": f"package-manager:{manager}", "path": manager_paths[manager]}
        for manager in sorted(managers)
    )
    return {
        "languages": sorted(language_paths),
        "package_managers": sorted(managers),
    }, evidence


def _command_facts(
    repository: Path, files: list[Path], stack: dict[str, list[str]]
) -> tuple[dict[str, str], list[dict[str, str]]]:
    file_names = {file.as_posix() for file in files}
    commands: dict[str, str] = {}
    evidence_paths: dict[str, str] = {}
    if "package.json" in file_names:
        _package_json_commands(repository, stack, commands, evidence_paths)
    if "pyproject.toml" in file_names:
        _pyproject_commands(repository, commands, evidence_paths)
    if "Makefile" in file_names:
        _makefile_commands(repository, commands, evidence_paths)

    ordered = {name: commands[name] for name in sorted(commands)}
    evidence = [
        {"fact": f"command:{name}", "path": evidence_paths[name]}
        for name in sorted(evidence_paths)
    ]
    return ordered, evidence


def _package_json_commands(
    repository: Path,
    stack: dict[str, list[str]],
    commands: dict[str, str],
    evidence_paths: dict[str, str],
) -> None:
    try:
        payload = json.loads((repository / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    scripts = payload.get("scripts", {})
    if not isinstance(scripts, dict):
        return
    manager = _javascript_manager(stack["package_managers"])
    for name in COMMAND_NAMES:
        if name not in scripts:
            continue
        commands[name] = (
            f"{manager} test"
            if manager == "npm" and name == "test"
            else f"{manager} run {name}"
        )
        evidence_paths[name] = "package.json"


def _javascript_manager(managers: list[str]) -> str:
    for candidate in ("pnpm", "yarn", "bun", "npm"):
        if candidate in managers:
            return candidate
    return "npm"


def _pyproject_commands(
    repository: Path, commands: dict[str, str], evidence_paths: dict[str, str]
) -> None:
    try:
        with (repository / "pyproject.toml").open("rb") as handle:
            payload = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return
    tools = payload.get("tool", {})
    candidates = {
        "test": ("pytest", "python -m pytest"),
        "lint": ("ruff", "ruff check ."),
        "typecheck": ("mypy", "mypy ."),
    }
    for name, (tool, command) in candidates.items():
        if tool in tools and name not in commands:
            commands[name] = command
            evidence_paths[name] = "pyproject.toml"
    if "pyright" in tools and "typecheck" not in commands:
        commands["typecheck"] = "pyright"
        evidence_paths["typecheck"] = "pyproject.toml"


def _makefile_commands(
    repository: Path, commands: dict[str, str], evidence_paths: dict[str, str]
) -> None:
    try:
        makefile = (repository / "Makefile").read_text(encoding="utf-8")
    except OSError:
        return
    targets = set(re.findall(r"^([A-Za-z0-9_.-]+)\s*:", makefile, flags=re.MULTILINE))
    for name in COMMAND_NAMES:
        if name in targets and name not in commands:
            commands[name] = f"make {name}"
            evidence_paths[name] = "Makefile"


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
