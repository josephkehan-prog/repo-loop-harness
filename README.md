# RepoLoop

**Verified repository context and fail-closed guardrails for AI coding agents.**

[![CI](https://github.com/josephkehan-prog/repo-loop-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/josephkehan-prog/repo-loop-harness/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-65c7d0.svg)](LICENSE)

RepoLoop scans a local Git repository and compiles two inspectable contracts:

- a deterministic `RepoSnapshot` containing repository facts, commands, and evidence paths;
- a fail-closed `RepoCapsule` containing trust state, completion checks, permissions, and loop limits.

Use those contracts to give Codex, Claude Code, OpenCode, or another coding agent grounded repository context without trusting model guesses or loading the entire repository into one prompt.

> **Developer preview:** RepoLoop `0.1.0` implements read-only discovery, capsule compilation, CLI, TUI, browser GUI, and a reproducible proof command. It does not yet execute or verify agent-written code. The checkpointed runtime, isolated worktrees, and independent change verifier remain planned work.

![RepoLoop repository context and verification workflow](docs/workflow.svg)

## Why RepoLoop

Coding agents are good at producing code, but the system around the model still needs reliable answers:

- Which commands actually build, test, lint, and typecheck this repository?
- Which files prove those commands and stack choices?
- Is the working tree already dirty?
- What may an agent change, and which actions require approval?
- What evidence would count as completion?

RepoLoop answers the implemented portion mechanically. Repository facts come from deterministic scanners, every derived fact carries a repository-relative evidence path, and the default capsule begins quarantined with destructive actions denied.

RepoLoop is useful when you want:

- **AI coding agent guardrails** that are portable across model vendors;
- **repository context** with provenance instead of another generated summary;
- **local-first inspection** with no telemetry or cloud index;
- **machine-readable policy** for a future LangGraph, MCP, ACP, or custom runtime;
- **reproducible proof** of the scanner and capsule guarantees implemented today.

## Quick start

Requirements: Python 3.12+ and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/josephkehan-prog/repo-loop-harness.git
cd repo-loop-harness
uv sync --extra dev --locked

./repo-loop proof .
./repo-loop discover .
./repo-loop capsule show .
./repo-loop gui .
```

Install the CLI in an isolated tool environment:

```bash
uv tool install .
repo-loop --help
```

## Prove the implemented guarantees

Run the proof command before evaluating the architecture claims:

```bash
repo-loop proof /path/to/repository
repo-loop proof /path/to/repository --json
```

The command performs two independent scans and checks five properties:

| Check | Passing condition |
| --- | --- |
| Snapshot repeatable | Two scans of the same repository state are identical |
| Evidence paths portable | Every evidence path is repository-relative |
| Trust quarantined | A new capsule begins in `quarantined` state |
| Destructive actions denied | Default destructive permission is `deny` |
| External writes gated | Default external-write permission is `approval` |

It exits with status `0` only when every check passes. CI runs the same command against the checked-out project. See the [reproducible proof demo](docs/proof-demo.md) for the exact workflow and its limits.

## Inspect a repository

### CLI and JSON

```bash
# Human-readable repository identity and digest
repo-loop discover /path/to/repository

# Stable machine-readable snapshot
repo-loop discover /path/to/repository --json

# Fail-closed policy contract
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
  "fact_digest": "28fe49cc8609bbb3506a5370e9a4c038ae605d9ecbfba8a40b5233fc12f10143"
}
```

### Terminal UI

```bash
repo-loop tui /path/to/repository
```

The Textual interface provides Overview, Commands, Evidence, and Policy views. Press `r` to rescan and `q` to quit.

### Browser GUI

```bash
# Choose an available loopback port and open the browser
repo-loop gui /path/to/repository

# Serve without opening a browser
repo-loop gui /path/to/repository --no-open --port 4317
```

The inspection bench shows repository identity, Git state, capsule digest, detected stack, commands, evidence, permissions, completion checks, and loop ceilings.

The server binds only to `127.0.0.1`. It has no public-host option, telemetry, external assets, mutation endpoint, or HTTP path selector.

## Use the contracts with an agent

RepoLoop is agent-agnostic. Today, the portable handoff is JSON:

```bash
repo-loop capsule show . --json > /tmp/repo-capsule.json
```

An agent integration can read the capsule as untrusted repository context while machine policy remains authoritative. Runtime commands intentionally fail closed until a separate backend is configured:

```bash
export REPO_LOOP_BACKEND="/path/to/repo-loop-runtime-adapter"

repo-loop run understand . --mode discover
repo-loop run repair . --issue 123 --mode shadow
repo-loop resume SESSION_ID
repo-loop status SESSION_ID
```

Arguments are forwarded as an array without shell interpolation. Without `REPO_LOOP_BACKEND`, runtime commands return `EX_UNAVAILABLE`; RepoLoop never reports that a loop ran when no runtime exists.

## How it works

```text
local Git repository
    -> deterministic read-only scan
    -> RepoSnapshot with evidence
    -> fail-closed RepoCapsule
    -> CLI, TUI, GUI, or runtime adapter
```

### RepoSnapshot

A snapshot records only facts RepoLoop can prove for one repository state:

- Git root, HEAD, branch, and dirty paths;
- detected languages, package managers, and lockfiles;
- discovered build, test, lint, format, security, and typecheck commands;
- repository-relative evidence for every derived fact;
- a canonical SHA-256 digest over portable facts.

The scanner ignores dependency caches, build output, VCS internals, and symlinks. It does not write into the inspected repository.

### RepoCapsule

A capsule turns the snapshot into a portable policy contract:

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

Repository facts and machine policy remain separate. Repository instructions cannot grant credentials, tools, permissions, or external side effects.

### Planned governed loop

The target controller is deliberately bounded:

```text
preflight
  -> choose_work_item
  -> load_skill
  -> plan
  -> execute_in_isolation
  -> verify_outside_worker_context
  -> continue | retry_changed_strategy | approve | complete | stop
```

The controller owns state transitions. A separate verifier owns the completion verdict. For state contracts, retry rules, execution modes, and the full design, read [ARCHITECTURE.md](ARCHITECTURE.md).

## Security model

Repository content is untrusted input.

- Machine policy outranks repository instructions.
- Secrets never enter snapshots, capsules, browser responses, or logs.
- External writes require approval in the default capsule.
- Destructive actions are denied by default.
- The GUI uses a route allowlist, strict CSP, Host validation, cross-site request rejection, and text-only rendering of repository-derived values.
- The runtime adapter uses argument arrays with `shell=False`.

Report vulnerabilities privately through [GitHub Security Advisories](https://github.com/josephkehan-prog/repo-loop-harness/security/advisories/new). See [SECURITY.md](SECURITY.md).

## Current limits

RepoLoop does not currently:

- run a checkpointed coding loop;
- execute discovered build or test commands;
- create or manage worktrees;
- verify an agent-generated diff;
- route MCP tools or ACP agents;
- commit, push, open pull requests, or publish releases;
- send repository content to a model or hosted service.

These are explicit boundaries, not hidden degraded modes.

## Repository layout

```text
repo-loop-harness/
├── src/repo_loop/
│   ├── discovery.py       # deterministic scanner and capsule compiler
│   ├── proof.py           # reproducible contract verification
│   ├── cli.py             # CLI and runtime handoff
│   ├── tui.py             # Textual dashboard
│   ├── gui.py             # loopback HTTP server
│   └── web/               # packaged HTML, CSS, and JavaScript
├── tests/                 # unit, integration, TUI, GUI, and wrapper tests
├── docs/                  # workflow chart, proof, testing, and launch plan
├── ARCHITECTURE.md        # proposed governed-loop architecture
└── pyproject.toml
```

## Develop and verify

```bash
uv sync --extra dev --locked
uv run ruff check .
uv run coverage run -m unittest discover -s tests
uv run coverage report -m
uv run repo-loop proof . --json
uv build
uv export --locked --no-dev --no-emit-project --no-hashes | uvx pip-audit -r /dev/stdin
```

The test suite enforces an 80% branch-coverage floor. TDD evidence is recorded in [CLI and TUI tests](docs/testing/cli-tui-wrapper.tdd.md) and [GUI tests](docs/testing/gui.tdd.md).

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Participation is governed by the [RepoLoop Code of Conduct](CODE_OF_CONDUCT.md).

## Roadmap

- [x] Deterministic read-only repository discovery
- [x] Governed capsule compilation
- [x] CLI, TUI, local browser GUI, and proof report
- [x] Fail-closed runtime adapter boundary
- [ ] Broader instruction, ownership, entry-point, and deployment scanners
- [ ] SQLite checkpoints and resumable repository-understanding loop
- [ ] Controller with independent verifier
- [ ] Isolated worktree repair mode
- [ ] MCP and ACP capability routing with approval gates
- [ ] Managed signed commits, review mode, and release gates

## Origins and credit

RepoLoop is an independent implementation, not a fork. Its specification-first contracts, evidence ledger, evaluation boundary, adapter model, and resume semantics were inspired by the original [Q00/Ouroboros](https://github.com/Q00/ouroboros) project. Detailed attribution and project boundaries are centralized in [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md) so the README can explain RepoLoop itself without repeating the origin story throughout every section.

## License

RepoLoop is available under the [MIT License](LICENSE). Copyright remains with each respective project and contributor listed in [ACKNOWLEDGEMENTS.md](ACKNOWLEDGEMENTS.md).
