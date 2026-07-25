## Summary

Closes #202.

This PR cleans up and standardizes our `httpx2` integration by:
- Upgrading to `httpx2>=2.9.1` (which introduces process-wide `httpx2.alias_httpx()`) and `respx>=0.23.1`.
- Completely removing the third-party `pytest-httpx2` plugin dependency.
- Adding `src/sitecustomize.py` to invoke `httpx2.alias_httpx()` at Python interpreter startup before pytest plugin entrypoints load.

---

## Architectural Decisions & Implementation

1. **Interpreter Startup Aliasing (`src/sitecustomize.py`)**:
   - Python's built-in `site` module automatically executes `sitecustomize.py` at interpreter initialization time.
   - Placing `httpx2.alias_httpx()` in `src/sitecustomize.py` guarantees that `sys.modules["httpx"]` and `sys.modules["httpcore"]` are aliased to `httpx2` and `httpcore2` **before** pytest or setuptools entrypoint plugins (such as `respx`) are imported.

2. **Application Entrypoints**:
   - `src/ruff_sync/__init__.py` and `src/ruff_sync/__main__.py` also include `if "httpx" not in sys.modules: httpx.alias_httpx()` to ensure `httpx2` is aliased when `ruff-sync` is imported or executed as a CLI tool in any environment.

3. **Standard `respx` Mocking**:
   - Because `httpx` and `httpcore` are aliased process-wide before network requests take place, standard `respx` (`>=0.23.1`) mocks `httpx2` network calls natively out-of-the-box.
   - Removed `"pytest-httpx2"` from `pyproject.toml` without custom `HTTPCore2Mocker` classes or test fixture hacks.

4. **Fixture Compatibility**:
   - Added an `httpx2_mock` fixture alias in `tests/conftest.py` returning `respx_mock` to maintain backward compatibility with existing test function signatures.

---

## Verification

- `uv run ruff check . --fix`: Passed (0 errors)
- `uv run ruff format .`: Passed (0 errors)
- `uv run mypy .`: Passed (0 errors across 53 source files)
- `uv run pytest -vv`: Passed (**413 passed**, 1 xfailed)
