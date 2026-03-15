# AGENTS.md

## Project Overview

**ruff-sync** is a CLI tool that synchronizes [Ruff](https://docs.astral.sh/ruff/) linter configuration across multiple Python projects. It downloads an upstream `pyproject.toml`, extracts the `[tool.ruff]` section, and merges it into a local project's `pyproject.toml` while preserving formatting, comments, and whitespace.

- **GitHub Repository**: [`Kilo59/ruff-sync`](https://github.com/Kilo59/ruff-sync)
- The application uses a `src` layout in `src/ruff_sync/`.
- Dev tasks are defined in `tasks.py` using [Invoke](https://www.pyinvoke.org/).

## GitHub Context

This is a GitHub-hosted project. Use the **`gh` CLI** to gather extra context about issues, milestones, pull requests, and releases before starting work. This is especially useful for understanding the intent behind a task or finding related discussions.

### Useful Commands

```bash
# Issues
gh issue list                           # Open issues
gh issue view <number>                  # Read a specific issue with full context
gh issue list --milestone "v0.1"        # Issues for a specific milestone

# Pull Requests
gh pr list                              # Open PRs
gh pr view <number>                     # Read PR description, review comments, checks
gh pr checks <number>                   # See CI status for a PR
gh pr diff <number>                     # View the diff

# Milestones & Releases
gh api repos/Kilo59/ruff-sync/milestones  # List milestones
gh release list                           # List releases

# Labels
gh label list                           # See available labels
```

### When to Use `gh`

- **Before starting a task**: If the user references an issue number or milestone, read it with `gh issue view` to understand the full context, acceptance criteria, and any prior discussion.
- **During PR work**: Use `gh pr view` and `gh pr checks` to understand review feedback and CI status.
- **When investigating bugs**: Search issues with `gh issue list --search "<keywords>"` to find related reports or prior fixes.

## Tech Stack

- **Python** ≥ 3.10 (target version `py310`)
- **Package Manager**: [uv](https://docs.astral.sh/uv/) — Use `uv run <command>` for all executions to ensure the correct environment.
- **Linter / Formatter**: [Ruff](https://docs.astral.sh/ruff/) (`^0.15.0`)
- **Type Checker**: [mypy](https://mypy-lang.org/) (strict mode)
- **Test Framework**: [pytest](https://docs.pytest.org/) with `pytest-asyncio`, `respx`, `pyfakefs` (See [Testing Standards](.agents/TESTING.md))
- **Coverage**: `coverage` + Codecov
- **Pre-commit**: `pre-commit` / `prek` (see `.pre-commit-config.yaml`)
- **TOML Parsing**: [tomlkit](https://github.com/sdispater/tomlkit) — preserves formatting and comments
- **HTTP**: [httpx](https://www.python-httpx.org/) (async)

## Project Structure

```text
.agents/               # Agent-specific instructions (Deep Standards)
  TESTING.md           # Mandatory testing patterns and rules
  workflows/           # Step-by-step guides for common tasks
src/ruff_sync/         # The application source
  __init__.py          # Public API
  cli.py               # CLI, merging logic, HTTP
  __main__.py          # -m support
tasks.py               # Invoke tasks: lint, fmt, type-check, deps, new-case
pyproject.toml         # Project config, dependencies, ruff/mypy settings
tests/
  ruff.toml            # Test-specific ruff overrides (extends ../pyproject.toml)
  test_basic.py        # Unit tests for core functions
  test_corner_cases.py # Edge case tests for TOML merge logic
  test_whitespace.py   # Tests for whitespace/comment preservation during merge
  test_e2e.py          # End-to-end tests using lifecycle TOML fixtures
  test_project.py      # Tests that validate project config consistency
  test_toml_operations.py  # Tests for low-level TOML operations
  lifecycle_tomls/     # TOML fixture files (*_initial.toml, *_upstream.toml, *_final.toml)
```

After ANY code change, you MUST validate with the following tools, in this order. **ALWAYS prefix these commands with `uv run`**:

### 1. Lint with Ruff

```bash
uv run ruff check . --fix
```

- Ruff config lives in `pyproject.toml` under `[tool.ruff]` and `[tool.ruff.lint]`.
- Tests have additional overrides in `tests/ruff.toml` (extends the root config).
- All Python files must include `from __future__ import annotations` (enforced by isort rule `I002`).
- Use `uv run ruff check . --fix` to auto-fix issues. Use `--unsafe-fixes` only if explicitly asked.
- **Do NOT disable or ignore rules** unless the user explicitly asks you to.

#### Understanding a Rule

If you encounter an unfamiliar lint rule or need to understand why a rule exists:

```bash
uv run ruff rule <RULE_CODE>
```

For example: `uv run ruff rule TC006` explains the `TC006` rule in detail.
Use this to make informed decisions rather than blindly suppressing rules.

### 2. Format with Ruff

```bash
uv run ruff format .
```

- Line length: **90** characters.
- Docstring code formatting is enabled (`docstring-code-format = true`).
- Preview formatting features are enabled.

### 3. Type-check with mypy

```bash
uv run mypy .
```

- mypy is configured in strict mode with `python_version = "3.10"`.
- It checks `src/`, `tests/`, and `tasks.py`.
- Tests have relaxed rules: `type-arg` and `no-untyped-def` are disabled for `tests.*`.
- `tomlkit` returns complex union types — use `cast(Any, ...)` in tests when indexing parsed TOML documents to satisfy mypy without verbose type narrowing.

### 4. Run Tests

```bash
uv run pytest -vv
```

Or with coverage:

```bash
uv run coverage run -m pytest -vv
```

- Coverage is tracked for `src/ruff_sync/` only.
- Tests use `respx` to mock HTTP calls and `pyfakefs` for filesystem mocking.
- `pytest-asyncio` is in **strict** mode — async tests need the `@pytest.mark.asyncio` decorator.

## Code Conventions

### Imports

- Always use `from __future__ import annotations` as the first import.
- Do NOT use `from pathlib import Path` or `from datetime import ...` — these are banned by the import conventions config. Use `import pathlib` and `import datetime as dt` instead.
- Imports used only for type hints should go inside `if TYPE_CHECKING:` blocks.

### Style

- Use `pathlib` over `os.path` (enforced by `PTH` rules).
- Prefer f-strings for logging (we ignore `G004`).
- Do not create custom exception classes for simple errors (`TRY003` is ignored).
- **Prefer `NamedTuple` for return types** over plain tuples to improve readability and type safety.

### TOML Handling

- **Always use `tomlkit`** for reading/writing TOML. It preserves formatting, comments, and whitespace — which is critical for this project's purpose.
- Be aware that `tomlkit` returns proxy objects. When you need to convert them to plain Python for comparisons or re-insertion, use `.unwrap()`.
- Dotted keys (e.g., `lint.select = [...]`) create proxy tables that behave differently from explicit table headers (`[tool.ruff.lint]`). The merge logic in `_recursive_update` handles this.

### Testing

- New TOML merge edge cases belong in `tests/test_corner_cases.py`.
- Whitespace/formatting preservation tests go in `tests/test_whitespace.py`.
- End-to-end lifecycle tests use fixture triples in `tests/lifecycle_tomls/` (`*_initial.toml`, `*_upstream.toml`, `*_final.toml`). Use the `invoke new-case` task to scaffold them.
- Tests should include **both** structural/whitespace assertions and **semantic** assertions (verifying the merged config values are correct).

## Invoke Tasks

Defined in `tasks.py`. **ALWAYS** run these through uv: `uv run invoke <task>`

| Task         | Alias                 | Description                            |
| ------------ | --------------------- | -------------------------------------- |
| `lint`       |                       | Lint with ruff (auto-fixes by default) |
| `fmt`        |                       | Format with ruff format                |
| `type-check` | `types`               | Type-check with mypy                   |
| `deps`       | `sync`                | Sync dependencies with uv              |
| `new-case`   | `new-lifecycle-tomls` | Scaffold lifecycle TOML fixtures       |

## CI

CI is defined in `.github/workflows/ci.yaml`:

- **Static Analysis**: runs `lint --check`, `fmt --check`, and `type-check` on Python 3.10.
- **Tests**: matrix across Python 3.10, 3.11, 3.12, 3.13, 3.14.
- **Pre-commit.ci**: auto-fixes and auto-updates hooks on PRs.

## Common Pitfalls

1. **tomlkit proxy objects**: When adding new keys to a proxy table (from dotted keys), the proxy must be converted to a real table first. The `_recursive_update` function handles this. Don't bypass it.
2. **`cast(Any, ...)` in tests**: Use `cast(Any, tomlkit.parse(...))["tool"]["ruff"]` pattern in tests to avoid mypy complaints about `tomlkit`'s `Item | Container` return types.
3. **Pre-commit ruff version**: The ruff version in `.pre-commit-config.yaml` must stay in sync with the version in `pyproject.toml`. The test `test_pre_commit_versions_are_in_sync` enforces this.
