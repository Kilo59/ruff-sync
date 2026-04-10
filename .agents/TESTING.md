# Testing Standards for ruff-sync

This document defines the mandatory testing standards and patterns for the `ruff-sync` project. AI agents MUST follow these guidelines when adding or modifying tests.

## 1. Core Principles

- **Every Fix Needs a Test**: Any bug fix must include a reproduction test that fails without the fix and passes with it.
- **No Side Effects**: Tests must be isolated and not touch the actual filesystem or make real network calls. Furthermore, tests must not pollute the CI environment (e.g., writing to `GITHUB_STEP_SUMMARY`). Always mock CI-specific environment variables using `monkeypatch.delenv` if the code under test interacts with them.
- **Semantic + Structural Assertions**: When testing TOML merges, always verify **both**:
  1. **Structural/Whitespace**: The file "looks" correct (comments and spacing are preserved).
  2. **Semantic**: The actual data in the merged result matches the expected values. Use the [dirty-equals](skills/dirty-equals/SKILL.md) Agent Skill for declarative, concise assertions.
- **DRY with Fixtures and Parameterization**: Avoid code duplication. Use fixtures for common setups and `@pytest.mark.parametrize` for matrix testing.

## 2. Tooling and Environment

- **Execution**: Always run tests using `uv run pytest -vv`.
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

### 3.3 No Autouse Fixtures
`autouse=True` fixtures are **never allowed**. They hide setup logic and can cause non-obvious side effects or dependencies between tests. All fixtures used by a test must be explicitly requested in the test function's arguments.

### 3.4 No unittest.mock
The use of `unittest.mock` or `MagicMock` is strictly forbidden because it encourages bad design and tests that lie to you. Any kind of patching is discouraged. Instead, follow these patterns:
1. **Dependency Injection (DI)**: Design code so that dependencies (like loggers or configurations) are passed in, rather than hard-coded. This allows for simple "Spies" or test-specific objects to be used without patching.
2. **Dedicated Libraries**: Use `respx` for HTTP and `pyfakefs` for filesystem operations to mock at the IO layer.
3. **Monkeypatch (as a last resort)**: If a dependency is truly external and not easily injectable (e.g., a global function in a library), use the built-in `monkeypatch` fixture. However, always check if the code can be redesigned for DI first.

### 3.5 Main Entry Point
Every test file **must** end with a main entry point block. This ensures each file is independently executable as a script (`python tests/test_foo.py`).

```python
if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
```

**Why this matters:**
1.  **Direct Execution**: Developers can run a single test file using standard Python without needing to remember complex `pytest` filter flags.
2.  **IDE Workflow Integration**: Many IDEs (like VS Code or PyCharm) allow you to run the "Current File" with a single click or keyboard shortcut. Having a main block ensures this works out of the box with the correct verbosity and scope.
3.  **Cleaner Diffs**: By terminating the file with this standard block, it prevents "no newline at end of file" warnings and ensures that new tests added above it produce clean, isolated diff segments. It also ensures that when debugging with `--icdiff` or similar tools, the output is scoped correctly to the specific file.

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
uv run invoke new-case --name <case_name> --description "Description of the edge case"
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

We target **high coverage** for `src/ruff_sync/`.
- Run coverage locally: `uv run coverage run -m pytest -vv && uv run coverage report`
- New features MUST include unit tests in `tests/test_basic.py` or specialized files like `tests/test_whitespace.py` if they involve formatting logic.
