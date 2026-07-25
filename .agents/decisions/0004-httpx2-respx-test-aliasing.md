# ADR 0004: httpx2 Integration, Respx Mocking, and Test-Guarded Process Aliasing

---
status: accepted
date: 2026-07-25
decider: Kilo59 / Agent
---

## Context & Motivation for Switching to `httpx2`

`ruff-sync` relies on an asynchronous HTTP client to pull upstream Ruff linter configurations from GitHub and GitLab repositories.

We migrated from `httpx` to **`httpx2`** based on the official rationale provided by **Pydantic Services**:
- **Active Stewardship & Security Maintenance**: Due to a significant period of reduced maintenance activity and inactivity on the original `httpx` package, Pydantic Services created `httpx2` as an actively maintained successor to guarantee timely security updates, bug fixes, and continuous maintenance for a critical core library in the Python ecosystem.
- **Ecosystem Continuity**: The "2" in `httpx2` functions as a versioning marker for this new era of Pydantic Services maintenance rather than a breaking paradigm rewrite, preserving full compatibility while delivering active upstream support.
- **Strict Typing**: `httpx2` provides first-class typing out of the box, integrating cleanly with our `mypy` strict mode requirements.

Previously, HTTP test mocking relied on the third-party `pytest-httpx2` plugin. We needed to clean up our HTTP dependencies, eliminate `pytest-httpx2`, and migrate to standard `respx` (`>=0.23.1`) while ensuring zero side-effects on production execution.

## Decision

1. **Direct Application Imports**: Application runtime code (`src/ruff_sync/core.py`) imports `httpx2` directly (`import httpx2 as httpx`).
2. **Elimination of `pytest-httpx2`**: We completely removed `pytest-httpx2` from dependencies due to confusion and transport hook coupling.
3. **Test-Guarded Process Aliasing (`src/sitecustomize.py`)**: We place `httpx2.alias_httpx()` inside `src/sitecustomize.py` guarded by a runtime check (`any("pytest" in arg for arg in sys.argv) or "PYTEST_CURRENT_TEST" in os.environ`).

## Rationale & Technical Tradeoffs

### 1. Removal of `pytest-httpx2`
Beyond introducing transport hook conflicts and entrypoint ordering bugs, `pytest-httpx2` caused developer confusion:
- `pytest-httpx2` is a wrapper around `respx`, but its name frequently leads developers to the documentation for `pytest-httpx` / `httpx_pytest`.
- This created confusion around fixture names, routing syntax, and unexpected mocking behavior.
Eliminating `pytest-httpx2` removes this confusing wrapper layer and standardizes our test suite directly on `respx`.

### 2. No Production HTTP Plugin Dependencies
`ruff-sync` runtime code does **not** depend on third-party `httpcore` or `httpx` plugins in production.
If our production runtime relied on external plugins that hard-coded `import httpx` or `import httpcore`, we would require process-wide aliasing at production application startup. Because `ruff-sync` manages its HTTP transport directly via `httpx2`, aliasing is only necessary during test suite execution when `respx` is loaded by Pytest.

### 3. Packaging Exclusion
`src/sitecustomize.py` lives outside `src/ruff_sync/` and is strictly excluded from wheel packages by Hatchling (`packages = ["src/ruff_sync"]`). Published `.whl` and `sdist` distributions never include or ship `sitecustomize.py` to end users.

### 4. Why Disabling `respx` Autoloading (`-p no:respx`) Is a Gnarly Upstream Problem
We evaluated disabling `respx` entrypoint autoloading via `addopts = ["-p", "no:respx"]` and manually declaring `pytest_plugins = ["respx"]` in `conftest.py`. However, this reveals a gnarly entrypoint race condition:
- `respx` registers a `pytest11` entrypoint that imports `httpx`/`httpcore` at plugin discovery time.
- Disabling `respx` autoloading and re-enabling it via `pytest_plugins` causes `respx` to initialize its `MockRouter` hooks *after* Python module resolution has settled. In end-to-end CLI tests where `httpx2.AsyncClient` is instantiated across sub-threads or CLI entrypoints, `httpx2` creates fresh `httpcore2` transport instances that bypass `respx`'s delayed transport hooks, causing `RESPX: some routes were not called!` errors.
- **Upstream Resolution Needed**: This conflict needs to be resolved **upstream** — either in `respx` (by deferring transport binding until active router context rather than entrypoint import time) or in `httpx2` (by providing native `httpcore2` transport interceptors for `respx` without requiring `sys.modules` aliasing). Until fixed upstream, `sitecustomize.py` is the only mechanism that forces `alias_httpx()` to run at Python interpreter launch before Pytest's entrypoint scanner initializes `respx`.

## References

- [ADR Index](./README.md)
- [httpx2 Migration Guide](https://httpx2.pydantic.dev/migration/)
- [Issue #202](https://github.com/Kilo59/ruff-sync/issues/202) / [PR #203](https://github.com/Kilo59/ruff-sync/pull/203)
