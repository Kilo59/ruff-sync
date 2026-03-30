# Formatter Pipeline Architecture

> **Purpose**: Reference document for agents and developers extending or maintaining
> `ruff_sync.formatters`. Covers the streaming vs. accumulating formatter taxonomy,
> the `finalize()` contract, how to add a new formatter, and the fingerprint strategy
> required by structured CI report formats (GitLab Code Quality, SARIF).
>
> **Source of truth**: `src/ruff_sync/formatters.py` and `src/ruff_sync/constants.py`.

---

## Overview

All human-readable and machine-readable output from the `check` and `pull`
commands flows through a single **`ResultFormatter` protocol**.  This keeps
`core.py` and `cli.py` agnostic about the output medium — the same drift
detection logic emits text to a terminal, GitHub Actions workflow commands, or
a GitLab Code Quality JSON report.

```
core.py / cli.py
      │
      │  fmt.error(message, file_path=..., drift_key="lint.select")
      │  fmt.warning(...)
      │  fmt.finalize()
      ▼
ResultFormatter  (Protocol)
      ├── TextFormatter      → stderr/stdout, human-readable
      ├── GithubFormatter    → ::error file=...:: workflow commands
      ├── JsonFormatter      → NDJSON, one record per line
      └── GitlabFormatter    → GitLab Code Quality JSON array (pending)
```

---

## The `ResultFormatter` Protocol

Defined in `src/ruff_sync/formatters.py`.

### Methods

| Method | When to call | Notes |
|---|---|---|
| `note(message)` | Status output that always prints (e.g. "Checking…") | Streaming; never buffered |
| `info(message, logger)` | Informational progress | Streaming |
| `success(message)` | Positive outcome (e.g. "In sync ✓") | Streaming |
| `error(message, file_path, logger, check_name, drift_key)` | Config drift or failure | See §Semantic Fields |
| `warning(message, file_path, logger, check_name, drift_key)` | Non-fatal issue (e.g. stale pre-commit hook) | See §Semantic Fields |
| `debug(message, logger)` | Verbose internal state | Streaming |
| `diff(diff_text)` | Unified diff between upstream and local | Intentionally ignored by structured formatters |
| `finalize()` | **Always called in a `try…finally` by `core.py`** | No-op for streaming; writes report for accumulating |

### Semantic Fields on `error()` and `warning()`

```python
def error(
    self,
    message: str,
    file_path: pathlib.Path | None = None,
    logger: logging.Logger | None = None,
    check_name: str = "ruff-sync/config-drift",   # machine-readable rule ID
    drift_key: str | None = None,                  # e.g. "lint.select"
) -> None: ...
```

- **`check_name`** — machine-readable rule identifier used by structured
  formatters (GitLab `check_name`, SARIF `ruleId`).  Defaults to
  `"ruff-sync/config-drift"`.  Use a distinct name for different issue
  classes; e.g. `"ruff-sync/precommit-stale"`.
- **`drift_key`** — the dotted TOML key that caused the drift (e.g.
  `"lint.select"`).  Used by accumulating formatters to build **stable,
  per-key fingerprints** without re-parsing the message string.  Pass
  `None` when the drift cannot be attributed to a single key.

---

## Formatter Taxonomy

### Streaming Formatters

Emit output immediately on each call.  `finalize()` is a no-op.

| Class | Format | Use |
|---|---|---|
| `TextFormatter` | Human text | Default terminal output |
| `GithubFormatter` | `::error file=…::` | GitHub Actions inline annotations |
| `JsonFormatter` | NDJSON | Machine consumption, piping, `jq` |

### Accumulating Formatters *(pending implementation)*

Collect issues internally and flush a single structured document in
`finalize()`.

| Class | Format | Use |
|---|---|---|
| `GitlabFormatter` | GitLab Code Quality JSON array | `artifacts: reports: codequality:` |
| `SarifFormatter` *(future)* | SARIF v2.1.0 | GitHub Advanced Security, other SAST tooling |

Key difference: accumulating formatters **must** have `finalize()` called
to produce any output.  The `try…finally` pattern in `cli.py` guarantees
this even when `UpstreamError` or another exception occurs.

---

## Adding a New Formatter

1. **Add the format value** to `OutputFormat` in `src/ruff_sync/constants.py`:
   ```python
   class OutputFormat(str, enum.Enum):
       TEXT   = "text"
       JSON   = "json"
       GITHUB = "github"
       GITLAB = "gitlab"
       SARIF  = "sarif"   # new
   ```

2. **Implement the class** in `src/ruff_sync/formatters.py`.  For a
   streaming formatter, all methods emit immediately and `finalize` is a
   no-op.  For an accumulating formatter:
   - Collect issues in `self._issues: list[...]` during `error()` / `warning()`.
   - Write the document in `finalize()` (to `stdout` — the caller pipes to
     a file).

3. **Add a `case`** in `get_formatter`:
   ```python
   def get_formatter(output_format: OutputFormat) -> ResultFormatter:
       match output_format:
           case OutputFormat.SARIF:
               return SarifFormatter()
           ...
   ```
   The `match` statement is **exhaustive** — mypy will error if a new
   `OutputFormat` value is not handled.

4. **Add tests** in `tests/test_formatters.py`.  At minimum:
   - `finalize()` on an empty formatter produces the correct "no issues"
     document (e.g. `[]` for GitLab, a valid SARIF run with zero results).
   - `error()` produces a record with the correct severity.
   - Fingerprints are stable across two identical calls.
   - `finalize()` on a streaming formatter emits nothing.

---

## `finalize()` Call Site

`finalize()` is always called in a `try…finally` block within `core.py`’s
`check()` and `pull()` coroutines:

```python
fmt = get_formatter(args.output_format)
try:
    ...
finally:
    fmt.finalize()   # no-op for streaming; flushes JSON for accumulating
```

`finalize()` is always called unconditionally — **do not** guard it with
`isinstance` or `hasattr` checks.  Every formatter in the protocol provides
the method.

---

## Fingerprint Strategy (Accumulating Formatters)

Stable fingerprints are required so CI platforms can track whether an issue
is newly introduced or already resolved between branches.

```python
import hashlib

def _make_fingerprint(upstream_url: str, local_file: str, drift_key: str | None) -> str:
    if drift_key:
        raw = f"ruff-sync:drift:{upstream_url}:{local_file}:{drift_key}"
    else:
        raw = f"ruff-sync:drift:{upstream_url}:{local_file}"
    return hashlib.md5(raw.encode()).hexdigest()
```

**Rules:**
- Must be deterministic — same inputs → same fingerprint every run.
- Must be unique per logical issue (different keys → different fingerprints).
- Must **not** include timestamps, UUIDs, or any runtime-variable data.

---

## Severity Mapping

| ruff-sync scenario | GitLab severity | SARIF level |
|---|---|---|
| Config key value differs | `major` | `error` |
| Key missing from local | `major` | `error` |
| Extra local key absent upstream | `minor` | `warning` |
| Pre-commit hook version stale | `minor` | `warning` |
| Upstream unreachable | `blocker` | `error` |

---

## Exit Codes (Unchanged by Formatter Choice)

| Code | Meaning |
|---|---|
| 0 | In sync |
| 1 | Config drift detected |
| 2 | CLI usage error (argparse) |
| 3 | Pre-commit hook drift |
| 4 | Upstream unreachable |

CI jobs should use `when: always` (GitLab) or `if: always()` (GitHub) to
upload structured reports regardless of exit code.

---

## References

- [`src/ruff_sync/formatters.py`](../src/ruff_sync/formatters.py)
- [`src/ruff_sync/constants.py`](../src/ruff_sync/constants.py)
- [`tests/test_formatters.py`](../tests/test_formatters.py)
- [`.agents/gitlab-reports.md`](./gitlab-reports.md) — GitLab Code Quality implementation spec
- [`issue-102-context.md`](./issue-102-context.md) — full feature context for Issue #102
