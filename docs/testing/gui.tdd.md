# Local GUI TDD evidence

## Contract

The browser workbench must:

- appear as a first-class `repo-loop gui [PATH]` command;
- bind to `127.0.0.1` and choose an available port by default;
- use the deterministic scanner and capsule compiler without repository writes;
- expose only packaged assets, health, and a fresh dashboard projection;
- reject unknown paths, traversal attempts, foreign hosts, and cross-site requests;
- return a strict content security policy and no cross-origin permission;
- render repository-derived values as text rather than injected HTML;
- provide working refresh and digest-copy controls;
- remain readable at desktop and narrow viewport sizes.

## RED

Signed commit `72dce10` introduced the GUI contract before the implementation. The focused suite failed because `repo_loop.gui` and the `gui` command did not exist:

```text
ModuleNotFoundError: No module named 'repo_loop.gui'
AssertionError: 'gui' not found in command help
```

The later foreign-host test also failed against the first green implementation before Host and fetch-origin checks were added.

## GREEN

The implementation adds:

- a standard-library loopback HTTP server with a fixed repository root;
- an allowlisted API and in-memory packaged assets;
- a responsive local-only inspection bench;
- CLI browser launch and `--no-open` / `--port` controls;
- security headers, Host validation, and cross-site request rejection.

Release evidence is produced by:

```bash
uv run ruff check .
uv run coverage run -m unittest discover -s tests
uv run coverage report -m
uv build
uv run pip-audit
gitleaks detect --source . --no-banner --redact
```

The interface was also opened from the packaged command and inspected at desktop and 390-pixel-wide viewports. Refresh was activated through the rendered control and the updated repository state was observed in the live DOM.

Final result: 24 tests pass, total branch coverage is 84 percent, the wheel contains all three web assets, no vulnerable dependency is reported, and the repository secret scan is clean.
