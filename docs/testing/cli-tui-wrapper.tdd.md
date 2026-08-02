# CLI and TUI wrapper TDD evidence

## Source

No external plan file was supplied. The journeys were derived from the requested CLI wrapper and TUI additions on 2026-08-01.

## User journeys

1. As a repository maintainer, I want deterministic discovery output so I can inspect repository facts without granting mutation access.
2. As a repository maintainer, I want a compiled capsule so I can review verification and permission policy before running an agent.
3. As a terminal user, I want a read-only dashboard so I can inspect the capsule without reading raw JSON.
4. As a runtime integrator, I want arguments forwarded without a shell so an adapter can execute loops without command interpolation.
5. As a safety reviewer, I want runtime commands to fail closed when no backend exists so an unavailable loop cannot report false success.

## RED and GREEN report

| Stage | Command | Result | Evidence |
|---|---|---|---|
| RED | `uv run --with textual==8.2.8 python -m unittest discover -s tests -v` | Expected failure | All three test modules failed with `ModuleNotFoundError: No module named 'repo_loop'`; the implementation did not exist. |
| First GREEN attempt | `uv run python -m unittest discover -s tests -v` | 13 pass, 2 fail, 1 error | Exposed package-manifest language detection, Git porcelain whitespace, and Textual 8 accessor compatibility defects. |
| Packaging rerun | `uv run --extra dev python -m unittest discover -s tests -v` | 15 pass, 1 fail | Exposed a test assumption that temporary directory names were already lowercase; capsule IDs intentionally normalize them. |
| GREEN | `uv run python -m unittest discover -s tests -v` | 17 pass | CLI, backend boundary, discovery, capsule, terminal-safety, wrapper, model, and headless TUI behaviors passed. |
| Coverage | `uv run --extra dev coverage run -m unittest discover -s tests && uv run --extra dev coverage report` | 86 percent | Exceeds the configured 80 percent project gate. |

## Test specification

| # | What is guaranteed | Test target | Type | Result |
|---|---|---|---|---|
| 1 | Help exposes discovery, capsule, TUI/runtime command groups | `CliTests.test_help_exposes_documented_command_groups` | Integration | PASS |
| 2 | Discovery and capsule commands emit parseable JSON | `CliTests.test_discover_prints_machine_readable_snapshot`, `test_capsule_show_prints_compiled_contract` | Integration | PASS |
| 3 | Invalid paths fail with a usage error | `CliTests.test_invalid_repository_path_is_a_usage_error` | Integration | PASS |
| 4 | Runtime commands fail closed without a backend | `CliTests.test_runtime_commands_fail_closed_without_backend` | Integration | PASS |
| 5 | Backend arguments are forwarded as an array without a shell | `CliTests.test_backend_receives_arguments_without_shell_interpolation` | Unit | PASS |
| 6 | The source-checkout wrapper executes directly | `WrapperEndToEndTests.test_repository_wrapper_is_directly_executable` | E2E | PASS |
| 7 | Repository facts and digests are deterministic | `DiscoveryTests.test_discovers_versioned_repository_facts_deterministically` | Integration | PASS |
| 8 | Dirty paths are observed without changing source files | `DiscoveryTests.test_marks_dirty_paths_without_modifying_repository` | Integration | PASS |
| 9 | Capsule defaults deny destructive actions and gate external writes | `DiscoveryTests.test_compiles_governed_capsule_from_snapshot` | Unit | PASS |
| 10 | Dashboard projection does not mutate snapshot or capsule inputs | `DashboardModelTests.test_model_projects_snapshot_and_policy_without_mutating_inputs` | Unit | PASS |
| 11 | TUI renders repository/runtime state and refreshes with `r` | `RepoLoopAppTests.test_app_boots_with_repository_facts_and_keyboard_contract` | E2E | PASS |
| 12 | TUI refresh uses the injected deterministic loader | `RepoLoopAppTests.test_app_uses_injected_discovery_for_repeatable_refresh` | Integration | PASS |
| 13 | Repository-derived control characters are escaped before terminal rendering | `TerminalPresentationTests.test_control_characters_are_escaped_before_terminal_rendering` | Security | PASS |

## Known gaps

- The implemented slice discovers languages, package managers, common commands, Git revision, and dirty paths. Instruction, ownership, deployment, and secrets-surface scanners remain future work.
- Runtime `run`, `resume`, and `status` behavior belongs to the external backend. This project currently verifies only fail-closed handoff.
- TUI tests are headless behavioral tests; pixel-level snapshot testing is not yet configured.
- `pip-audit` reported no known vulnerabilities in the locked runtime dependency set.

## Merge evidence

- RED checkpoint: `f294a13 test: define CLI and TUI contracts`.
- GREEN checkpoint: `feat: add executable CLI and TUI wrapper`.
