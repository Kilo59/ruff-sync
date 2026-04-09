# Feature Roadmap: Config Validation (Detailed)

This document provides a technical deep-dive into the "Config Validation" roadmap (originally #116), breaking down requirements for ensuring that synchronized Ruff configurations are valid, consistent, and future-proof.

## Overview

When `ruff-sync pull` is executed, it merges upstream configuration into a local file. Without validation, this process can:
1.  Introduce TOML syntax errors.
2.  Add configuration keys that are not supported by the local Ruff version.
3.  Set a `target-version` that exceeds the project's supported Python range.
4.  Include deprecated rules that will cause warnings in every local Ruff execution.

## Technical Requirements

### 1. Structural and CLI Validation (Priority: 🔴 High)

**Requirement**: `ruff-sync` must verify that the resulting TOML is both valid TOML and a valid Ruff configuration before overwriting local files.

*   **Logic**:
    1.  After merging but before writing to disk, serialize the `TOMLDocument` to a string.
    2.  Write this string to a temporary file (using `tempfile`).
    3.  Execute Ruff's own validation:
        ```bash
        ruff check --config <temp_file> --stdin-filename dummy.py < /dev/null
        ```
    4.  If the exit code is non-zero, capture `stderr`, report it to the user, and abort the sync.

### 2. Python Version Consistency Check (Priority: 🟠 Medium)

**Requirement**: Warn if the upstream `target-version` is more restrictive than the local `requires-python`.

*   **Logic**:
    1.  Read `requires-python` from `[project]` or `[tool.poetry]` in `pyproject.toml`.
    2.  Read `target-version` from the merged `[tool.ruff]`.
    3.  Compare the versions (e.g., using `packaging.version` or simple string comparison for `py3x`).
    4.  **Warning**: "⚠️ Upstream target-version (py312) is higher than local requires-python (>=3.10). This may lead to Ruff suggesting features incompatible with your project's Python support."

### 3. Rule Deprecation Detection (Priority: 🟡 Low)

**Requirement**: Detect and warn about rules that Ruff marks as deprecated.

*   **Logic**:
    1.  Capture `stderr` from the validation step in Priority 1.
    2.  Ruff typically outputs warnings like: `warning: `UP036` is deprecated and will be removed in a future release.`
    3.  Parse these lines and report them as `ruff-sync` warnings.

### 4. Protective "Strict" Mode (Priority: 🟢 Low)

**Requirement**: Provide a `--strict` flag to fail the sync if any warnings (Version mismatch, Deprecations) are found.

*   **Logic**:
    1.  Add `--strict` to `ruff-sync pull` and `ruff-sync check`.
    2.  If set, any validation warning or mismatch mentioned above results in an exit code `1` (or another error code) and prevents the file from being updated.

## Implementation Steps

### Phase 1: Core Validation Hook
Modify `ruff_sync.core.pull` to incorporate a "pre-flight" validation step using a temporary file and `ruff check`.

### Phase 2: Metadata Extraction
Implement utilities in `src/ruff_sync/system.py` or a new `validation.py` to extract Python version constraints from the local environment and the TOML.

### Phase 3: CLI Integration
Update `ruff_sync.cli.Arguments` to include the `--strict` flag and pass it through to the core logic.

## Expected CLI Experience

```text
$ ruff-sync pull
🔄 Syncing Ruff...
⚠️ Upstream config uses deprecated rule 'UP036', which may be removed in future Ruff versions.
⚠️ Upstream target-version (py311) > local project support (>=3.10).
✅ Updated pyproject.toml
```

```text
$ ruff-sync pull --strict
🔄 Syncing Ruff...
❌ Validation Failed: Upstream config uses deprecated rule 'UP036'.
💥 Sync aborted due to --strict mode.
```
