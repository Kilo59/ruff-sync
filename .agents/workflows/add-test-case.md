---
description: How to add a new lifecycle TOML test case for ruff-sync
---

Follow these steps to add a new end-to-end (E2E) test case for `ruff-sync` to test a specific sync or merge scenario.

### 1. Identify the Edge Case or Bug

- Clearly define the "Initial" state (local `pyproject.toml`) and the "Upstream" state (remote `pyproject.toml`).
- Define the "Final" expected state after the sync.

### 2. Scaffold the Fixture

// turbo

1. Run the `new-case` task to generate the file triple:
   ```bash
   uv run invoke new-case --name <case_name> --description "Description of the test case"
   ```
   _Replace `<case_name>` with a simple name (e.g., `dotted_keys`). This creates files in `tests/lifecycle_tomls/`._

### 3. Edit the Fixtures

1. Edit `tests/lifecycle_tomls/<case_name>_initial.toml` with the local starting state.
2. Edit `tests/lifecycle_tomls/<case_name>_upstream.toml` with the remote config (must contain a `[tool.ruff]` section).
3. Edit `tests/lifecycle_tomls/<case_name>_final.toml` with the expected result of the merge.

### 4. Run the E2E Test Suite

// turbo

1. Execute the tests to ensure the new case is picked up:
   ```bash
   uv run pytest -vv tests/test_e2e.py
   ```
   _The E2E suite automatically discovers all file triples in the `lifecycle_tomls/` directory._

### 5. Validate Formatting and Types

// turbo

1. Ensure the new TOML files don't break any project rules:
   ```bash
   uv run invoke lint --check
   uv run invoke types
   ```
