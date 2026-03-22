# Contributing

Thank you for your interest in contributing to `ruff-sync`!

This page covers the essentials. For the full contributor's guide, see [CONTRIBUTING.md](https://github.com/Kilo59/ruff-sync/blob/main/CONTRIBUTING.md) on GitHub.

---

## Getting Started

1. **Fork & clone** the repository.
2. **Install [uv](https://docs.astral.sh/uv/)**, then sync dependencies:
   ```bash
   uv run invoke deps
   ```
3. **Install pre-commit hooks**:
   ```bash
   uv run pre-commit install
   ```

---

## Documentation Preview

You can preview the documentation locally using Invoke:

```bash
# Build and serve locally (localhost:8000)
uv run invoke docs

# Build only
uv run invoke docs --build
```

---

## Quality Checks

Run these before every commit, in order:

```bash
uv run ruff check . --fix   # Lint & auto-fix
uv run ruff format .         # Format
uv run mypy .                # Type-check
uv run pytest -vv            # Tests
```

> [!IMPORTANT]
> Fix lint errors at the source — do **not** add `# noqa` or suppress rules in config.

---

## Writing Tests

- Use `pyfakefs` for filesystem, `respx` for HTTP mocking.
- Async tests need `@pytest.mark.asyncio`.
- TOML merge tests need both a **structural** (whitespace/comments preserved) and a **semantic** (values are correct) assertion.
- Scaffold new lifecycle TOML test cases with:
  ```bash
  uv run invoke new-case --name <case> --description "..."
  ```

See [`.agents/TESTING.md`](https://github.com/Kilo59/ruff-sync/blob/main/.agents/TESTING.md) for detailed testing standards.

---

## Contributing a Curated Config

We welcome new configurations in [`configs/`](https://github.com/Kilo59/ruff-sync/tree/main/configs)!

👉 **[Join the discussion on Issue #83](https://github.com/Kilo59/ruff-sync/issues/83)** before submitting.

1. Create `configs/<my-domain>/ruff.toml` with inline comments on each rule.
2. Optionally add a `README.md` explaining the config's goals.
3. Open a PR referencing [Issue #83](https://github.com/Kilo59/ruff-sync/issues/83).

See [Pre-defined Configs](pre-defined-configs.md) for the existing examples.

---

## Reporting Bugs

[Open an issue](https://github.com/Kilo59/ruff-sync/issues/new) with:
- `ruff-sync --version` output.
- `ruff --version` output.
- Your operating system and Python version.
- The command you ran and its full output.
- Relevant `pyproject.toml` excerpts.

---

## Pull Request Tips

- Branch off `main`; keep commits focused.
- For significant changes, open an issue first.
- Ensure all CI checks pass before requesting review.
