# Testing Standards for ruff-sync

This document defines the mandatory testing standards and patterns for the `ruff-sync` project. AI agents MUST follow these guidelines when adding or modifying tests.

## 1. Core Principles

- **Every Fix Needs a Test**: Any bug fix must include a reproduction test that fails without the fix and passes with it.
- **No Side Effects**: Tests must be isolated and not touch the actual filesystem or make real network calls.
- **Semantic + Structural Assertions**: When testing TOML merges, always verify **both**:
  1. **Structural/Whitespace**: The file "looks" correct (comments and spacing are preserved).
  2. **Semantic**: The actual data in the merged result matches the expected values.
- **DRY with Fixtures and Parameterization**: Avoid code duplication. Use fixtures for common setups and `@pytest.mark.parametrize` for matrix testing.

## 2. Tooling and Environment

- **Execution**: Always run tests using `poetry run pytest -vv`.
- **Async Tests**: We use `pytest-asyncio` in **strict mode**.
  - Always decorate async tests with `@pytest.mark.asyncio`.
- **HTTP Mocking**: Use [respx](https://github.com/lundberg/respx) for all network interactions.
- **FS Mocking**: Use [pyfakefs](https://jmcgeheeiv.github.io/pyfakefs/) for file-based tests.

## 3. Best Practices and Patterns

### 3.1 Use Pytest Fixtures
Avoid re-defining common TOML strings or setup logic in every test function. Use fixtures to provide consistent test data.

```python
@pytest.fixture
def sample_ruff_config() -> str:
    return """[tool.ruff]
target-version = "py310"
lint.select = ["F", "E"]
"""
```

### 3.2 Parameterization
Use `@pytest.mark.parametrize` to test the same logic against multiple scenarios. Use `pytest.param(..., id="case_name")` to ensure test reports are readable.

```python
@pytest.mark.parametrize(
    "source, upstream, expected_keys",
    [
        pytest.param("[tool.ruff]\nselect=[]", "select=['F']", {"select"}, id="simple-add"),
        pytest.param("[tool.ruff]\nignore=['E']", "ignore=['W']", {"ignore"}, id="simple-merge"),
    ]
)
def test_merge_scenarios(source, upstream, expected_keys):
    # ... test logic ...
```

## 4. Handling TOML and `tomlkit`

`tomlkit` is central to this project but its dynamic type system can be tricky for mypy.

### The "Proxy" Problem
`tomlkit` often returns "proxy" objects (like dotted keys) that don't always behave like standard dicts.
- **Assertion Pattern**: To satisfy mypy when indexing into a parsed document in tests, use the `cast(Any, ...)` pattern:
  ```python
  from typing import Any, cast
  import tomlkit

  doc = tomlkit.parse(content)
  # Cast the document or table to Any before deep indexing
  ruff_cfg = cast(Any, doc)["tool"]["ruff"]
  assert ruff_cfg["target-version"] == "py310"
  ```
- **Comparison**: Use `list()` or `.unwrap()` if you need to compare `tomlkit` arrays/objects to standard Python types.

## 4. Lifecycle TOML Fixtures

For end-to-end (E2E) testing of the sync/merge logic, use the "Lifecycle" pattern.

### Fixture Triples
Each test case consists of three files in `tests/lifecycle_tomls/`:
1.  `<case_name>_initial.toml`: The starting project state.
2.  `<case_name>_upstream.toml`: The remote ruff config to sync from.
3.  `<case_name>_final.toml`: The expected result after merge.

### Scaffolding New Cases
Use the provided Invoke task to create a new case from a template:
```bash
poetry run invoke new-case --name <case_name> --description "Description of the edge case"
```

## 5. Standard Assertions for Merges

When testing `merge_ruff_toml`, your test body should look like this:

```python
def test_my_edge_case():
    source_s = "..."
    upstream_s = "..."

    source_doc = tomlkit.parse(source_s)
    upstream_ruff = cast(Any, tomlkit.parse(upstream_s))["tool"]["ruff"]

    merged_doc = ruff_sync.merge_ruff_toml(source_doc, upstream_ruff)
    merged_s = merged_doc.as_string()

    # 1. Structural check (e.g., check for comment preservation)
    assert "# Important comment" in merged_s

    # 2. Semantic check (the "Source of Truth")
    merged_data = tomlkit.parse(merged_s)
    ruff = cast(Any, merged_data)["tool"]["ruff"]
    assert ruff["lint"]["select"] == ["F", "E"]
```

## 6. Code Coverage

We target **high coverage** for `ruff_sync.py`.
- Run coverage locally: `poetry run coverage run -m pytest -vv && poetry run coverage report`
- New features MUST include unit tests in `tests/test_basic.py` or specialized files like `tests/test_whitespace.py` if they involve formatting logic.
