# Contributing to ruff-sync

Thank you for your interest in contributing! This guide covers everything you need to know to get set up and make a great contribution.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Running the Quality Checks](#running-the-quality-checks)
- [Writing Tests](#writing-tests)
- [Submitting a Pull Request](#submitting-a-pull-request)
- [Contributing a Curated Config](#contributing-a-curated-config)
- [Reporting Bugs](#reporting-bugs)
- [Code of Conduct](#code-of-conduct)

---

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone git@github.com:<your-username>/ruff-sync.git
   cd ruff-sync
   ```
3. **Install [uv](https://docs.astral.sh/uv/)** — our package manager:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
4. **Sync dependencies**:
   ```bash
   uv run invoke deps
   ```
5. **Install pre-commit hooks**:
   ```bash
   uv run pre-commit install
   ```

---

## Development Setup

The project uses a `src` layout. All source code lives in `src/ruff_sync/`. Development tasks are managed via [Invoke](https://www.pyinvoke.org/) in `tasks.py`.

| Task | Alias | Description |
|---|---|---|
| `uv run invoke lint` | | Lint with Ruff (auto-fixes by default) |
| `uv run invoke fmt` | | Format with Ruff |
| `uv run invoke type-check` | `types` | Type-check with mypy |
| `uv run invoke deps` | `sync` | Sync dependencies with uv |
| `uv run invoke new-case` | `new-lifecycle-tomls` | Scaffold lifecycle TOML test fixtures |

---

## Making Changes

- **Branch off `main`** for all new work:
  ```bash
  git checkout -b my-feature
  ```
- **Keep commits focused**: one logical change per commit is ideal.
- **Follow code conventions** (see below).

### Code Conventions

- Always add `from __future__ import annotations` as the first import in every Python file.
- Use `import pathlib` (not `from pathlib import Path`) and `import datetime as dt` (not `from datetime import ...`).
- Use `pathlib` for all path manipulation (enforced by `PTH` rules).
- **Always use `tomlkit`** for reading or writing TOML — it preserves comments, whitespace, and formatting.
- Prefer `NamedTuple` for multi-value return types.
- Type hints everywhere; the project uses mypy in strict mode.

---

## Running the Quality Checks

Before pushing, always run the full quality suite in this order:

```bash
# 1. Lint (auto-fixes where possible)
uv run ruff check . --fix

# 2. Format
uv run ruff format .

# 3. Type-check
uv run mypy .

# 4. Tests
uv run pytest -vv
```

> [!IMPORTANT]
> **Do not add `# noqa` comments or suppress lint rules.** Fix the underlying issue instead.

CI runs the same checks across Python 3.10–3.14, so make sure everything passes locally first.

---

## Writing Tests

All new behavioural changes and bug fixes **must** include tests. See the [Testing Standards](.agents/TESTING.md) for a full guide, but the key rules are:

- **No real filesystem or network calls**: Use `pyfakefs` for filesystem and `respx` for HTTP mocking.
- **Async tests** need `@pytest.mark.asyncio` (strict mode is on).
- **TOML merge tests** need both a structural check (comments/whitespace preserved) and a semantic check (actual values are correct).
- Every test file must end with:
  ```python
  if __name__ == "__main__":
      pytest.main([__file__, "-vv"])
  ```

### Lifecycle TOML Fixtures

For end-to-end merge testing, use the fixture triple pattern:

```bash
# Scaffold a new test case
uv run invoke new-case --name <case_name> --description "What this edge case tests"
```

This creates three files in `tests/lifecycle_tomls/`: `<case>_initial.toml`, `<case>_upstream.toml`, and `<case>_final.toml`.

---

## Submitting a Pull Request

1. Push your branch and open a PR against `main`.
2. Fill in the PR description: what changed, why, and how to test it.
3. Ensure all CI checks pass.
4. A maintainer will review your PR — please respond to feedback promptly.

> [!TIP]
> For significant changes, open an issue first to discuss the approach before investing time in an implementation.

---

## Contributing a Curated Config

We actively welcome community-contributed Ruff configurations! These live in the [`configs/`](./configs/) directory and are documented in the [Pre-defined Configs Guide](https://kilo59.github.io/ruff-sync/pre-defined-configs/).

**Join the discussion in [Issue #83](https://github.com/Kilo59/ruff-sync/issues/83)** before submitting a new config.

### What makes a good curated config?

- Targeted at a clear use case (e.g., `configs/cli-tools/ruff.toml`).
- Each rule or group of rules has an inline comment explaining *why* it's enabled.
- Has been tested against real-world projects in that domain.

### Steps

1. Create a new directory under `configs/` (e.g., `configs/my-domain/`).
2. Add a `ruff.toml` with well-commented rules.
3. Optionally add a `README.md` in the directory explaining the config's goals.
4. Open a PR referencing [Issue #83](https://github.com/Kilo59/ruff-sync/issues/83).

---

## Reporting Bugs

Please [open an issue](https://github.com/Kilo59/ruff-sync/issues/new) with:
- The `ruff-sync` version (`ruff-sync --version`).
- The `ruff` version (`ruff --version`).
- Your operating system and Python version.
- The command you ran and its full output.
- Your local `pyproject.toml` (or relevant snippets).

---

## Code of Conduct

Please be respectful and constructive in all project spaces.
