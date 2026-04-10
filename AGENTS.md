# AGENTS.md

## Project Overview

**ruff-sync** is a CLI tool that synchronizes [Ruff](https://docs.astral.sh/ruff/) linter configuration across multiple Python projects. It downloads an upstream `pyproject.toml`, extracts the `[tool.ruff]` section, and merges it into a local project's `pyproject.toml` while preserving formatting, comments, and whitespace.

- **GitHub Repository**: [`Kilo59/ruff-sync`](https://github.com/Kilo59/ruff-sync)
- The application uses a `src` layout in `src/ruff_sync/`.
- Dev tasks are defined in `tasks.py` using [Invoke](https://www.pyinvoke.org/).

## GitHub Context

Use the GitHub CLI (`gh`) to gather extra context about issues, pull requests, and releases before starting work. For detailed workflows on managing issues, see the `gh-issues` skill in `.agents/skills/gh-issues/SKILL.md`.

## Agent Skills

Specific workflows, libraries, and tools are documented in `.agents/skills/`. Before using unfamiliar tools like Textual, generating MkDocs, or asserting test data structures, check this directory for specialized best practices. If you create a new skill, use the `skill-creator` tool and avoid documenting full details here to prevent bloat.

## Tech Stack

- **Python** ≥ 3.10 (target version `py310`)
- **Package Manager**: [uv](https://docs.astral.sh/uv/) — Use `uv run <command>` for all executions to ensure the correct environment.
    - **Note on PATH**: On macOS, `uv` is often installed in `~/.local/bin`. If `uv` is not found, add this to your `PATH`: `export PATH="$PATH:$HOME/.local/bin"`.
- **Linter / Formatter**: [Ruff](https://docs.astral.sh/ruff/) (`>=0.15.0`)
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
  decisions/           # Internal Architectural Decision Records (ADRs)
    README.md          # Index of all architectural decisions
  skills/
    ruff-sync-usage/   # Agent Skill for users adopting ruff-sync (keep current!)
      SKILL.md
      references/
        configuration.md
        troubleshooting.md
        ci-integration.md
src/ruff_sync/         # The application source
  __init__.py          # Public API
  __main__.py          # CLI entry point (`python -m ruff_sync`)
  cli.py               # CLI argparse definition and orchestration
  constants.py         # Project-wide constants and default values
  core.py              # Core logic for merging, syncing, and repository handling
  formatters.py        # Logic for CLI output formatting (GitHub, GitLab, etc.)
  pre_commit.py        # Support for pre-commit hook generation and validation
tasks.py               # Invoke tasks: lint, fmt, type-check, deps, new-case, release
pyproject.toml         # Project config, dependencies, ruff/mypy settings
tests/
  conftest.py          # Shared pytest fixtures (mocking, temp dirs)
  ruff.toml            # Test-specific ruff overrides (extends ../pyproject.toml)
  test_basic.py        # Unit tests for core functions
  test_check.py        # Tests for --check mode and drift detection
  test_ci_integration.py # CI-specific environment tests
  test_ci_validation.py # Environment variable and CI output detection tests
  test_config_validation.py # Validation of local configuration
  test_constants.py    # Tests for internal constants and sentinels
  test_corner_cases.py # Edge case tests for TOML merge logic
  test_deprecation.py  # Tests for handling of deprecated flags/settings
  test_e2e.py          # End-to-end tests using lifecycle TOML fixtures
  test_formatters.py   # Serialization and formatting tests
  test_git_fetch.py    # Mocked git repository fetching tests
  test_pre_commit.py   # Pre-commit hook generation and sync tests
  test_project.py      # Tests that validate project config consistency
  test_scaffold.py     # Tests for the new-case scaffold task
  test_serialization.py # Tests for tomlkit serialization edge cases
  test_toml_operations.py # Tests for low-level TOML operations
  test_url_handling.py # Tests for GitHub and GitLab URL parsing
  test_whitespace.py   # Tests for whitespace/comment preservation during merge
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
- **Do NOT disable or ignore rules** unless the user explicitly asks you to. You must **fix the underlying code** to pass the linter, rather than appending `# noqa` directives or adding rules to `ignore` in `pyproject.toml`.

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

- Line length: **100** characters.
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
- **Do NOT use `unittest.mock` or `MagicMock`**. This project forbids `unittest.mock` because it encourages bad design and tests that lie to you. Prefer Dependency Injection (DI) and dedicated IO-layer libraries (respx, pyfakefs) over any kind of patching.
- Imports used only for type hints should go inside `if TYPE_CHECKING:` blocks.

### Style

- Use `pathlib` over `os.path` (enforced by `PTH` rules).
- Prefer f-strings for logging (we ignore `G004`).
- Do not create custom exception classes for simple errors (`TRY003` is ignored).
- **Prefer `NamedTuple` for return types** over plain tuples to improve readability and type safety.
- **Prefer `typing.Protocol` over `abc.ABC`** for abstract base classes to promote structural subtyping.
- **Prefer Dependency Injection (DI)**: Pass dependencies as arguments to functions and classes instead of hard-coding them or relying on global state. This makes code easier to test without patching.

### TOML Handling

- **Always use `tomlkit`** for reading/writing TOML. It preserves formatting, comments, and whitespace — which is critical for this project's purpose.
- Be aware that `tomlkit` returns proxy objects. When you need to convert them to plain Python for comparisons or re-insertion, use `.unwrap()`.
- Dotted keys (e.g., `lint.select = [...]`) create proxy tables that behave differently from explicit table headers (`[tool.ruff.lint]`). The merge logic in `_recursive_update` handles this.

### Sentinels & Missing Values

- Use the `MissingType.SENTINEL` (aliased as `MISSING`) from `ruff_sync.constants` whenever you need to distinguish between a value that is functionally "absent" and one that was explicitly provided (even if that provided value matches the default, such as `None` or an empty list).
- **Why?**: This is particularly important for configuration serialization, as it allows `ruff-sync` to distinguish between a setting the user actively chose and one that is simply the default. This keeps the user's `pyproject.toml` clean by ensuring only explicit choices are serialized.
- **Serialization Rule**: Only serialize fields to `[tool.ruff-sync]` if they are `not MISSING`.
- Example pattern for resolving configuration (note: use **truthiness**, not `is not None`, so an
  empty string falls back to config/defaults):
  ```python
  def _resolve_branch(args: Any, config: Mapping[str, Any]) -> str | MissingType:
      # Empty string is treated as falsy → falls back to config or DEFAULT_BRANCH
      if getattr(args, "branch", None):
          return cast("str", args.branch)
      if "branch" in config:
          return cast("str", config["branch"])
      return MISSING
  ```
  The actual MISSING → default resolution (e.g. `MISSING` → `"main"`) is handled in
  `resolve_defaults` from `ruff_sync.constants`, which is the single source of truth used
  by both `cli.main` and `core._merge_multiple_upstreams`.

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
| `docs`       |                       | Build or serve documentation           |
| `release`    |                       | Tag and create a GitHub release        |

## CI

CI is defined in `.github/workflows/ci.yaml`:

- **Static Analysis**: runs `lint --check`, `fmt --check`, and `type-check` on Python 3.10.
- **Tests**: matrix across Python 3.10, 3.11, 3.12, 3.13, 3.14.
- **Pre-commit.ci**: auto-fixes and auto-updates hooks on PRs.

## Common Pitfalls

1. **tomlkit proxy objects**: When adding new keys to a proxy table (from dotted keys), the proxy must be converted to a real table first. The `_recursive_update` function handles this. Don't bypass it.
2. **`cast(Any, ...)` in tests**: Use `cast(Any, tomlkit.parse(...))["tool"]["ruff"]` pattern in tests to avoid mypy complaints about `tomlkit`'s `Item | Container` return types.
3. **Pre-commit ruff version**: The ruff version in `.pre-commit-config.yaml` must stay in sync with the version in `pyproject.toml`. The test `test_pre_commit_versions_are_in_sync` enforces this.
4. **Keep `ruff-sync-usage` current**: Update `.agents/skills/ruff-sync-usage/` after any CLI behavior changes (flags, config keys, exits) to ensure the documentation stays accurate. Keep details inside the skill directory.
5. **No `autouse=True` fixtures**: NEVER use `autouse=True` for pytest fixtures. All fixtures must be explicitly requested by the test functions that require them. This ensures dependencies are explicit and avoids hidden side effects.

## Browser Tool Usage

- **Prefer `read_url_content`**: If you only need to extract text or markdown from a public URL, use `read_url_content`. It is faster and lighter.
- **Visual Interaction as Last Resort**: Only use `read_browser_page` or manual screen control when a page requires JavaScript execution, authentication, or complex visual interaction.
- **Task Specificity**: When using the browser subagent, provide highly specific tasks and clear exit criteria to minimize redundant interactions.

## Architectural Decision Records (ADRs)

Significant architectural shifts and long-term design decisions are recorded as ADRs in `.agents/decisions/`. These serve as the "memory" of the project's evolution for both human and agent developers.

- **Source of Truth**: Always check the [ADR Index](.agents/decisions/README.md) before proposing major architectural changes.
- **Process**: New decisions should be captured using the [adr skill](.agents/skills/adr/SKILL.md).
