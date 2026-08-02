# Reproduce RepoLoop's proof

> RepoLoop currently proves deterministic repository discovery and fail-closed capsule defaults. It does not yet prove that an AI coding agent produced a correct change.

This demo gives maintainers a fast, repeatable way to evaluate the guarantees implemented in the current release.

## Run the proof

From a RepoLoop checkout:

```bash
uv sync --extra dev --locked
uv run repo-loop proof .
```

The command exits with status `0` only when every implemented contract check passes.

For automation, request JSON:

```bash
uv run repo-loop proof . --json
```

The report contains:

| Field | Meaning |
| --- | --- |
| `result` | `pass` only when all checks pass |
| `repository` | Repository identity and Git state used for the proof |
| `snapshot_digest` | Canonical digest of the discovered portable facts |
| `completion_checks` | Build-quality commands discovered from repository files |
| `checks` | Individual contract results |
| `summary` | Passed and failed check counts |

## What is verified

The proof performs two scans against the same repository state and verifies:

1. Both snapshots are identical.
2. Every evidence path is relative to the repository.
3. A new capsule begins quarantined.
4. Destructive actions are denied by default.
5. External writes require approval by default.

The test suite also records Git status before and after the proof and confirms that tracked source content remains unchanged.

## Run the complete quality gate

```bash
uv run ruff check .
uv run coverage run -m unittest discover -s tests
uv run coverage report -m
uv run repo-loop proof . --json
uv build
uv export --locked --no-dev --no-emit-project --no-hashes | uvx pip-audit -r /dev/stdin
```

GitHub Actions runs the same lint, test, coverage, proof, build, and dependency-audit sequence on Python 3.12 and 3.13.

## Record a 90-second demonstration

Use one unfamiliar public repository and keep the recording unedited:

1. Show `git status --short` so the initial repository state is visible.
2. Run `repo-loop proof .` and show the five checks.
3. Run `repo-loop discover . --json` and highlight commands with their evidence paths.
4. Open `repo-loop gui .` and inspect the same digest and policy visually.
5. Run `git status --short` again to show that inspection created no repository changes.

Publish the repository URL, exact RepoLoop commit, Python version, commands, and terminal transcript with the recording. That makes the demonstration independently reproducible.

## Claims this demo does not support

Do not use this proof to claim that RepoLoop:

- improves an agent's task-completion rate;
- catches incorrect agent-generated patches;
- securely isolates a coding agent;
- executes tests or enforces their result;
- provides a working LangGraph, MCP, or ACP runtime.

Those claims require the planned governed runtime and a separate benchmark comparing agent runs with and without RepoLoop.

## Next benchmark

After the runtime exists, evaluate at least 20 fixed tasks across 10 public repositories. Run each task with the same model, budget, and starting revision in two conditions:

| Condition | Context and control |
| --- | --- |
| Baseline | Agent default repository exploration and verification |
| RepoLoop | RepoCapsule context, isolated worktree, bounded retries, and independent verification |

Measure task completion, invalid completion claims, out-of-scope files touched, verification commands skipped, wall time, agent turns, and cost. Publish every fixture and failed run, not only aggregate wins.
