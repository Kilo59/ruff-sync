# Feature Context: Richer CI output (Issue #102)

This document provides all technical specifications and context required to complete the enhancements for the `ruff-sync check` command. No additional research is needed.

## 1. Objective
Enhance the `check` command to support structured output formats (JSON, SARIF) and GitHub Actions inline annotations, while refining exit codes to distinguish between different failure modes.

## 2. Current Architecture

The project has already transitioned to a **Protocol-based formatting pipeline**. All output from the `check` and `pull` commands must flow through the `ResultFormatter` protocol.

### Location: `src/ruff_sync/formatters.py`
The `ResultFormatter` protocol defines how diagnostics are reported:

```python
class ResultFormatter(Protocol):
    def note(self, message: str) -> None: ...
    def info(self, message: str, logger: logging.Logger | None = None) -> None: ...
    def success(self, message: str) -> None: ...
    def error(self, message: str, file_path: pathlib.Path | None = None, logger: logging.Logger | None = None) -> None: ...
    def warning(self, message: str, file_path: pathlib.Path | None = None, logger: logging.Logger | None = None) -> None: ...
    def debug(self, message: str, logger: logging.Logger | None = None) -> None: ...
    def diff(self, diff_text: str) -> None: ...
```

### Existing Implementations:
- `TextFormatter`: Default human-readable output.
- `JsonFormatter`: Structured JSON output (emits one JSON record per line).
- `GithubFormatter`: Emits GitHub Actions workflow commands (e.g., `::error file=...::`).

## 3. Exit Code Specification (Final)

The following exit codes MUST be strictly enforced to ensure zero collisions with `argparse` or existing hook logic:

| Code | Meaning | Implementation Status |
|---|---|---|
| **0** | **In sync** | ✅ Implemented |
| **1** | **Config drift detected** | ✅ Implemented |
| **2** | **CLI usage error** | ✅ Handled by `argparse` |
| **3** | **Pre-commit hook drift** | ❌ **REQUIRED**: Move from code 2 to 3. |
| **4** | **Upstream unreachable** | ❌ **REQUIRED**: Catch `UpstreamError` and return 4. |

## 4. Pending Task: Granular Drift Reporting

Currently, `ruff-sync` reports if a file has drifted but does not specify which keys changed. For structured formats (JSON/SARIF), we need a list of the specific dotted keys that differ.

### Requirement:
1.  Implement `_find_changed_keys(source: Table, merged: Table) -> list[str]` in `src/ruff_sync/core.py`.
2.  It should recursively walk both tables and return a list of keys like `["lint.select", "target-version"]`.
3.  Update `ResultFormatter` to optionally accept this list, or ensure it is included in the diagnostic messages.

## 5. Pending Task: SARIF Output (`SarifFormatter`)

Implement the `SarifFormatter` class in `src/ruff_sync/formatters.py`.

### SARIF Requirements (v2.1.0):
- **Tool**: `ruff-sync`
- **Rule ID**: `RUFF-SYNC-CONFIG-DRIFT`
- **Level**: `error` if config drifted, `warning` if pre-commit drifted.
- **Message**: Must include the specific keys that drifted if available.
- **Location**: Must point to the local configuration file (e.g., `pyproject.toml`).

## 6. Implementation Checklist

- [ ] **`core.py`**:
    - [ ] Add `_find_changed_keys` helper.
    - [ ] Update `check()` to return code **3** for pre-commit drift.
    - [ ] Update `check()` and `pull()` to pass granular drift info to formatters.
- [ ] **`cli.py`**:
    - [ ] Update `main()` to catch `UpstreamError` and return exit code **4**.
- [ ] **`formatters.py`**:
    - [ ] Implement `SarifFormatter`.
    - [ ] Update `get_formatter` to include `"sarif"`.
- [ ] **Documentation**:
    - [ ] Update `.agents/skills/ruff-sync-usage/references/ci-integration.md` exit codes.

## 7. Verification Plan

1.  **Test Case**: Verify `ruff-sync check --pre-commit` returns exit code **3** when hooks are stale.
2.  **Test Case**: Verify `ruff-sync check` returns exit code **4** when the upstream URL is 404.
3.  **Test Case**: Verify `ruff-sync check --output-format sarif` produces valid SARIF JSON.
