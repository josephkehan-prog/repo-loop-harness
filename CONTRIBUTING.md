# Contributing to RepoLoop

Thank you for helping make repository agents safer, more deterministic, and easier to verify.

## Before you begin

- Search existing issues before opening a new one.
- Keep changes focused on one concern.
- Do not include credentials, proprietary repository content, or personal data in issues, fixtures, logs, or screenshots.
- Use GitHub Security Advisories instead of public issues for vulnerabilities.

## Local setup

```bash
git clone https://github.com/josephkehan-prog/repo-loop-harness.git
cd repo-loop-harness
uv sync --extra dev
```

## Development workflow

1. Add or update a failing test for behavioral changes.
2. Implement the smallest complete change.
3. Run the focused tests while iterating.
4. Run the full quality gate before submitting.
5. Update documentation when behavior, commands, policy, or public interfaces change.

```bash
uv run ruff check .
uv run coverage run -m unittest discover -s tests
uv run coverage report -m
uv build
uv export --locked --no-dev --no-emit-project --no-hashes | uvx pip-audit -r /dev/stdin
```

The full suite must pass with at least 80% branch coverage.

## Pull requests

A good pull request includes:

- a concise problem statement;
- the chosen behavior and safety boundary;
- tests proving the change;
- verification commands and results;
- documentation updates where relevant;
- no unrelated formatting or generated-file churn.

Repository-derived text is untrusted input. Changes involving filesystem paths, HTTP surfaces, command execution, secrets, authentication, external APIs, or mutation modes require an explicit security review.

By contributing, you agree that your contribution is licensed under the repository's MIT License.
