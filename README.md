# RepoLoop

**A local-first repository agent harness for compiling Git repositories into governed, evidence-backed agent capsules.**

[![CI](https://github.com/josephkehan-prog/repo-loop-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/josephkehan-prog/repo-loop-harness/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-65c7d0.svg)](LICENSE)

RepoLoop turns a software repository into a deterministic `RepoSnapshot` and a fail-closed `RepoCapsule`: verified facts, discovered commands, evidence paths, trust state, permissions, loop limits, and completion criteria. The capsule is the contract a bounded AI coding agent can use without loading an entire repository into one enormous prompt.

> RepoLoop is an independent implementation inspired by [Q00/Ouroboros](https://github.com/Q00/ouroboros), the original specification-first workflow engine for AI coding agents. See [Acknowledgements](ACKNOWLEDGEMENTS.md) for attribution and project boundaries.

![RepoLoop repository agent workflow](docs/workflow.svg)

## Why RepoLoop?

Most repository agents fail in familiar ways: they lose constraints in oversized context, trust worker self-reports, retry without changing strategy, collide with dirty work, or allow repository text to expand machine policy.

RepoLoop makes the missing boundaries explicit:

- **Deterministic discovery** — facts come from scanners, not model guesses.
- **Evidence provenance** — stack and command facts point back to repository files.
- **Fail-closed policy** — new repositories begin quarantined; destructive actions are denied.
- **Bounded loops** — iteration, attempt, budget, and stall limits are part of the capsule.
- **Independent verification** — a worker cannot approve its own result.
- **Local-first operation** — current interfaces perform read-only discovery with no target-repository writes.
- **Replaceable runtime** — future LangGraph, MCP, or other agent backends sit behind an explicit adapter boundary.

## Current status

RepoLoop `0.1.0` implements the read-only foundation:

- deterministic repository scanner;
- governed capsule compiler;
- machine-readable CLI;
- interactive Textual TUI;
- responsive loopback-only browser GUI;
- explicit external runtime adapter that fails closed when unconfigured.

The checkpointed LangGraph executor, isolated worktree mutation modes, and MCP capability routing are planned—not silently simulated by the current release.

## Quick start

Requirements: Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/josephkehan-prog/repo-loop-harness.git
cd repo-loop-harness
uv sync

./repo-loop discover .
./repo-loop capsule show .
./repo-loop gui .
```

Install the command in an isolated tool environment:

```bash
uv tool install .
repo-loop --help
```

## Interfaces

### Browser GUI

```bash
# Choose an available local port and open the browser
repo-loop gui /path/to/repository

# Serve without opening a browser
repo-loop gui /path/to/repository --no-open --port 4317
```

The inspection bench shows repository identity, Git state, capsule digest, detected stack, commands, evidence, permissions, completion checks, and loop ceilings. Use **Refresh repository** to rescan and **Copy digest** to copy the current capsule identity.

The GUI binds only to `127.0.0.1`. It has no public-host option, no telemetry, no external assets, no mutation endpoint, and no way to select a different filesystem path through HTTP.

### Terminal UI

```bash
repo-loop tui /path/to/repository
```

The TUI provides Overview, Commands, Evidence, and Policy views. Press `r` to rescan and `q` to quit.

### CLI and JSON

```bash
# Human-readable repository facts
repo-loop discover /path/to/repository

# Stable machine-readable snapshot
repo-loop discover /path/to/repository --json

# Compile and inspect the governed capsule
repo-loop capsule show /path/to/repository --json
```

Example snapshot shape:

```json
{
  "schema_version": 1,
  "repository": {
    "name": "example",
    "branch": "main",
    "dirty": false
  },
  "stack": {
    "languages": ["python"],
    "package_managers": ["uv"]
  },
  "commands": {
    "test": "python -m pytest"
  },
  "evidence": [
    {"fact": "language:python", "path": "src/example/__init__.py"}
  ],
  "fact_digest": "…"
}
```

### Runtime adapter

Runtime commands are intentionally unavailable until a separate backend is configured:

```bash
export REPO_LOOP_BACKEND="/path/to/repo-loop-runtime-adapter"

repo-loop run understand /path/to/repository --mode discover
repo-loop run repair /path/to/repository --issue 123 --mode shadow
repo-loop resume SESSION_ID
repo-loop status SESSION_ID
```

Arguments are forwarded as an array without shell interpolation. Without `REPO_LOOP_BACKEND`, runtime commands return `EX_UNAVAILABLE`; RepoLoop never pretends a loop ran successfully.

## How it works

```text
repository + explicit goal + policy
    -> deterministic RepoSnapshot
    -> governed RepoCapsule
    -> bounded loop session
    -> independent verification
    -> verified result or resumable stop
```

### RepoSnapshot

A snapshot records only facts RepoLoop can prove about one repository state:

- Git root, HEAD, branch, and dirty paths;
- languages, package managers, and lockfiles;
- discovered build, test, lint, format, security, and typecheck commands;
- repository-relative evidence for each derived fact;
- a canonical SHA-256 digest over the portable facts.

The scanner ignores dependency caches, build output, VCS internals, and symlinks. It does not write into the inspected repository.

### RepoCapsule

A capsule turns the snapshot into a portable agent policy contract:

```yaml
schema_version: 1
repo_id: example-4f92d8a3c610
trust: quarantined

verification:
  completion_requires: [lint, test]

loop:
  max_iterations: 12
  max_attempts_per_item: 3
  stall_limit: 3

permissions:
  external_write: approval
  destructive: deny
  secrets: vault-only
```

Capsules separate repository facts from machine policy. Repository instructions cannot grant tools, credentials, permissions, or external side effects.

### Planned loop controller

The target checkpointed graph is:

```text
preflight
  -> choose_work_item
  -> load_skill
  -> plan
  -> execute
  -> verify
  -> reflect_on_evidence
  -> continue | retry_changed_strategy | approve | complete | stop
```

Workers perform assigned actions. The controller owns state transitions. Independent verification owns the completion verdict.

For schemas, retry rules, execution modes, persistence, and the full LangGraph design, read [ARCHITECTURE.md](ARCHITECTURE.md).

## Security model

Repository content is untrusted input.

- Machine policy outranks repository instructions.
- Secrets never enter snapshots, capsules, browser responses, or logs.
- External writes require explicit approval.
- Destructive actions are denied by the default capsule.
- The GUI uses a fixed route allowlist, strict CSP, Host validation, cross-site request rejection, and text-only rendering of repository-derived values.
- The runtime adapter uses argument arrays with `shell=False`.

Please report vulnerabilities privately through [GitHub Security Advisories](https://github.com/josephkehan-prog/repo-loop-harness/security/advisories/new). See [SECURITY.md](SECURITY.md).

## Repository layout

```text
repo-loop-harness/
├── src/repo_loop/
│   ├── discovery.py       # deterministic scanner and capsule compiler
│   ├── cli.py             # command-line interface and runtime handoff
│   ├── tui.py             # Textual dashboard
│   ├── gui.py             # loopback HTTP server
│   └── web/               # packaged HTML, CSS, and JavaScript
├── tests/                 # unit, integration, TUI, GUI, and wrapper tests
├── docs/                  # workflow chart and TDD evidence
├── ARCHITECTURE.md        # complete runtime design
└── pyproject.toml
```

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run coverage run -m unittest discover -s tests
uv run coverage report -m
uv build
uv export --locked --no-dev --no-emit-project --no-hashes | uvx pip-audit -r /dev/stdin
```

The test suite enforces an 80% branch-coverage floor. Current TDD evidence is recorded in [CLI/TUI tests](docs/testing/cli-tui-wrapper.tdd.md) and [GUI tests](docs/testing/gui.tdd.md).

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Roadmap

- [x] Deterministic read-only repository discovery
- [x] Governed capsule compilation
- [x] CLI, TUI, and local browser GUI
- [x] Fail-closed runtime adapter boundary
- [ ] Broader instruction, ownership, entry-point, and deployment scanners
- [ ] SQLite checkpoints and resumable repository-understanding loop
- [ ] LangGraph controller with independent verifier
- [ ] Isolated worktree repair mode
- [ ] MCP capability discovery and approval routing
- [ ] Managed signed commits, review mode, and release gates

## Frequently asked questions

### What is a repository agent harness?

A repository agent harness supplies an AI coding agent with verified repository facts, bounded tools, explicit policy, stop conditions, and independent completion checks. It is the control layer around a model—not the model itself.

### Does RepoLoop modify repositories?

The current `discover`, `capsule`, `tui`, and `gui` interfaces are read-only. Planned mutation modes will use isolated worktrees and explicit promotion levels.

### Does RepoLoop use LangGraph today?

Not yet. The capsule and state contracts are designed for a checkpointed LangGraph controller, but `0.1.0` ships the deterministic discovery layer first.

### Is RepoLoop an Ouroboros fork?

No. RepoLoop is an independent repository-agent implementation inspired by Ouroboros concepts such as specification-first execution, ledgers, evaluation, runtime adapters, and resume semantics. The original Ouroboros project receives explicit credit in [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md).

### Why not load the entire repository into the model context?

Large undifferentiated prompts dilute constraints and provenance. RepoLoop compiles a small, deterministic capsule and pulls deeper context only when a selected task requires it.

## Attribution and license

RepoLoop is MIT licensed. Architectural inspiration and third-party project credits are documented in [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md). Copyright remains with each respective project and contributor.
