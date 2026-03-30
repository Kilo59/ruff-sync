# GitLab CI Artifacts Reports — Implementation Reference for ruff-sync

> **Purpose**: This document captures everything an agent needs to implement a fully compliant
> GitLab CI artifacts report for `ruff-sync`. It is self-contained; no extra research is needed.
>
> **Source docs**:
> - https://docs.gitlab.com/ci/yaml/artifacts_reports/
> - https://docs.gitlab.com/ci/testing/code_quality/
> - https://docs.astral.sh/ruff/integrations/#gitlab-cicd

---

## 1. The GitLab Report Landscape (Overview)

GitLab supports many `artifacts: reports:` types. The ones relevant to a Python linter/drift tool are:

| Report type | Tier | Best fit for ruff-sync? |
|---|---|---|
| `codequality` | Free | ✅ **Yes — primary target** |
| `junit` | Free | Possible but designed for test pass/fail, not lint |
| `sast` | Free (display in MR) | Overkill — security-focused format |
| `annotations` | Free (GitLab ≥ 16.3) | Simple external links only, limited |

**Use `codequality`**. It is the standard, Free-tier report type for linter/style violations. It displays inline in MR diffs (Ultimate) and in the MR widget (Free) as "introduced" vs "resolved" issues, and in the pipeline Code Quality tab (Premium+).

---

## 2. Key Behavior Rules for `artifacts: reports:`

These apply to **all** report types and are critical to get right:

1. **Always uploaded regardless of job exit code.** Even if the job fails, the artifact is
   uploaded. This is the whole point — you want the report even when drift is detected.

2. **`artifacts:expire_in` is separate from `artifacts:reports:`.** Reports have no implicit
   expiry; set it explicitly. GitLab defaults `codequality` to `1 week` automatically when
   the built-in CodeClimate template is used, but for custom jobs you must set it yourself.

3. **To browse the raw file in the GitLab UI**, you must *also* add `artifacts:paths:` pointing
   to the same file. `artifacts:reports:codequality:` alone only makes the report parseable by
   GitLab; it does not make the file downloadable/browsable without `paths:`.

4. **Multiple jobs can emit `codequality` reports** in the same pipeline. GitLab merges them
   automatically for the MR widget and pipeline view.

5. **Child pipeline `codequality` reports appear in MR annotations** but are NOT shared with
   the parent pipeline. (Known limitation — tracked in epic 8205.)

---

## 3. Code Quality Report Format (the JSON Schema)

GitLab's Code Quality report is a **JSON array** (not an object, not NDJSON). Each element is an
**issue object**. This format derives from the
[CodeClimate spec](https://github.com/codeclimate/platform/blob/master/spec/analyzers/SPEC.md),
but GitLab only reads a subset of fields.

### 3.1 Required Fields

Every issue object MUST have all of the following:

```json
{
  "description": "Human-readable description of the issue",
  "check_name":  "machine-readable-rule-id",
  "fingerprint": "unique-stable-hash-string",
  "severity":    "minor",
  "location": {
    "path":  "relative/path/to/file.toml",
    "lines": {
      "begin": 1
    }
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `description` | string | Shown in the MR widget and diff annotation. Keep it concise and human-readable. |
| `check_name` | string | Machine-readable rule identifier. Snake_case or kebab-case. Shown in the Code Quality tab. |
| `fingerprint` | string | **Must be unique and stable.** Used to detect whether an issue was introduced or resolved between branches. Same issue = same fingerprint across runs. If the fingerprint changes, GitLab treats it as a new issue. |
| `severity` | string | Must be one of: `info`, `minor`, `major`, `critical`, `blocker`. |
| `location.path` | string | Path to the file with the issue. **Must be relative to the repo root.** Do NOT use absolute paths. Do NOT use `./` prefix (although GitLab tolerates it). |
| `location.lines.begin` | integer | Line number where the issue begins (1-indexed). |

> [!IMPORTANT]
> The alternative `location.positions.begin.line` is also accepted (equivalent to
> `location.lines.begin`). Use `lines.begin` — it is simpler and more widely supported.

### 3.2 Optional Fields (Ignored by GitLab but harmless)

The full CodeClimate spec supports many more fields (`categories`, `content`, `remediation_points`,
etc.). GitLab silently ignores them — they won't break parsing but won't appear in the UI either.

### 3.3 Minimal Valid Example

```json
[
  {
    "description": "'lint.select' has drifted from upstream: expected ['E', 'F', 'W'], got ['E', 'F']",
    "check_name": "ruff-sync/config-drift",
    "fingerprint": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
    "severity": "major",
    "location": {
      "path": "pyproject.toml",
      "lines": {
        "begin": 1
      }
    }
  }
]
```

### 3.4 Empty Report (No Drift)

When `ruff-sync check` finds no drift, emit an **empty JSON array**:

```json
[]
```

Do NOT omit the file or output `null`. An empty array is the correct "no issues found" signal.
GitLab will use this to mark previously reported issues as "resolved."

---

## 4. Fingerprint Requirements (Critical Gotcha)

The fingerprint is the **most common source of bugs** in Code Quality integrations.

### Rules

- **Must be deterministic**: Same inputs → same fingerprint across all pipeline runs.
- **Must be unique per issue**: Different issues in the same file must have different fingerprints.
- **Must be stable**: If a key drifts, it should produce the same fingerprint whether the pipeline
  ran today or last week, as long as the logical issue is the same.
- **MD5 hex string is the conventional format**. GitLab's own examples use `7815696ecbf1c96e6894b779456d330e` (32-char hex). Any consistent hash works.
- **Do NOT include line numbers in the fingerprint input** (if lines are unstable). For ruff-sync,
  since we always point to line 1, including it is fine.

### Recommended Fingerprint Strategy for ruff-sync

For a "config drift" issue per key (e.g., `lint.select`), a good stable fingerprint is:

```python
import hashlib

def make_fingerprint(upstream_url: str, local_file: str, drift_key: str) -> str:
    """Stable fingerprint for a config drift issue."""
    raw = f"ruff-sync:drift:{upstream_url}:{local_file}:{drift_key}"
    return hashlib.md5(raw.encode()).hexdigest()
```

For a coarse "whole file drifted" issue (no per-key granularity yet):

```python
def make_fingerprint(upstream_url: str, local_file: str) -> str:
    raw = f"ruff-sync:drift:{upstream_url}:{local_file}"
    return hashlib.md5(raw.encode()).hexdigest()
```

> [!WARNING]
> Do NOT use `uuid.uuid4()` or any random value. That produces a new fingerprint each run, which
> causes GitLab to think every issue is freshly introduced — breaking the "resolved" tracking.

---

## 5. Severity Mapping for ruff-sync

| ruff-sync scenario | Recommended severity |
|---|---|
| Config drift detected (key value differs) | `major` |
| Pre-commit hook version stale | `minor` |
| Key missing from local config (upstream has it, local doesn't) | `major` |
| Key present locally but absent upstream (extra local config) | `minor` |
| Upstream unreachable (can't check) | `blocker` (or emit no report) |

---

## 6. `.gitlab-ci.yml` Job Definition

### 6.1 Minimal Correct Job

```yaml
ruff-sync-check:
  stage: lint
  image: python:3.12-slim
  before_script:
    - pip install ruff-sync
  script:
    # Exit code 1 = drift detected; we want the report even on failure
    - ruff-sync check --output-format gitlab > gl-code-quality-report.json || true
  artifacts:
    when: always          # Upload even if the job fails or has drift
    reports:
      codequality: gl-code-quality-report.json
    paths:
      - gl-code-quality-report.json   # Needed to browse/download the raw file
    expire_in: 1 week
```

> [!IMPORTANT]
> `when: always` is essential. Without it, if `ruff-sync check` exits with code 1 (drift found),
> GitLab treats the job as failed and does NOT upload the artifact — you lose the report.
>
> Alternatively, use `|| true` (or `|| exit 0`) in the script to always exit 0, then set the job
> to succeed. This is simpler but hides the failure signal. Use `when: always` instead so the job
> can still be marked as failed while the artifact is uploaded.

### 6.2 With `allow_failure` (Recommended for Linting Jobs)

```yaml
ruff-sync-check:
  stage: lint
  allow_failure: true     # Don't block the pipeline on drift
  script:
    - ruff-sync check --output-format gitlab > gl-code-quality-report.json
  artifacts:
    when: always
    reports:
      codequality: gl-code-quality-report.json
    paths:
      - gl-code-quality-report.json
    expire_in: 1 week
```

### 6.3 Using `uv` (Recommended for ruff-sync's own CI)

```yaml
ruff-sync-check:
  stage: lint
  image: python:3.12-slim
  before_script:
    - pip install uv
    - uv sync
  script:
    - uv run ruff-sync check --output-format gitlab > gl-code-quality-report.json
  artifacts:
    when: always
    reports:
      codequality: gl-code-quality-report.json
    paths:
      - gl-code-quality-report.json
    expire_in: 1 week
  allow_failure: true
```

---

## 7. Implementing `GitlabFormatter` in `formatters.py`

The goal is a new `OutputFormat.GITLAB` mode (alongside `text`, `json`, `github`). Unlike the
streaming formatters (`TextFormatter`, `JsonFormatter`), **Code Quality reports must be
accumulated and written as a single JSON array at the end** — not streamed line by line.

### 7.1 Key Design Constraint: `finalize()` Pattern

The Code Quality report must be a single valid JSON array. This means the formatter must:

1. Collect all issues into an internal list during the job.
2. Write the JSON array to the output file when the job finishes.

This requires adding a `finalize(output_path: pathlib.Path) -> None` method (or similar) to the
formatter, or adapting the `ResultFormatter` protocol.

**Option A — `GitlabFormatter` writes to a file (recommended)**:

```python
class GitlabFormatter:
    """GitLab Code Quality report formatter."""

    def __init__(self) -> None:
        self._issues: list[dict[str, Any]] = []

    def error(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
        check_name: str = "ruff-sync/config-drift",
        fingerprint: str | None = None,
    ) -> None:
        (logger or LOGGER).error(message)
        self._issues.append(self._make_issue(
            description=message,
            check_name=check_name,
            severity="major",
            file_path=file_path,
            fingerprint=fingerprint,
        ))

    def warning(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
        check_name: str = "ruff-sync/config-drift",
        fingerprint: str | None = None,
    ) -> None:
        (logger or LOGGER).warning(message)
        self._issues.append(self._make_issue(
            description=message,
            check_name=check_name,
            severity="minor",
            file_path=file_path,
            fingerprint=fingerprint,
        ))

    def _make_issue(
        self,
        description: str,
        check_name: str,
        severity: str,
        file_path: pathlib.Path | None,
        fingerprint: str | None,
    ) -> dict[str, Any]:
        path = str(file_path) if file_path else "pyproject.toml"
        fp = fingerprint or self._auto_fingerprint(description, path)
        return {
            "description": description,
            "check_name": check_name,
            "fingerprint": fp,
            "severity": severity,
            "location": {"path": path, "lines": {"begin": 1}},
        }

    @staticmethod
    def _auto_fingerprint(description: str, path: str) -> str:
        import hashlib
        raw = f"ruff-sync:drift:{path}:{description}"
        return hashlib.md5(raw.encode()).hexdigest()

    def finalize(self, output_path: pathlib.Path) -> None:
        """Write the collected issues as a JSON array to the output file."""
        output_path.write_text(json.dumps(self._issues, indent=2))
```

**Option B — `GitlabFormatter` writes to stdout as a JSON array at the end** (simpler for
piping with `>`):

```python
    def finalize(self) -> None:
        """Print the collected issues as a JSON array to stdout."""
        print(json.dumps(self._issues, indent=2))
```

With Option B, the CLI caller does `ruff-sync check --output-format gitlab > report.json`.

> [!NOTE]
> Option B is simpler and consistent with how the `github` and `json` formatters work (they
> both write to stdout). The caller redirects to a file. Option A is more explicit but requires
> adding a `--output-file` CLI flag or hardcoding the filename.

### 7.2 Protocol Impact

The current `ResultFormatter` protocol does NOT include `finalize()`. Adding `GitlabFormatter`
requires either:

1. **Add `finalize()` to the protocol** — all existing formatters get a no-op default.
2. **Keep `finalize()` off the protocol** — call it explicitly only when `output_format == GITLAB`.

Option 2 is cleaner in the short term (the existing `get_formatter` callers don't need changes).

### 7.3 `OutputFormat` enum extension

Add `GITLAB = "gitlab"` to the `OutputFormat` enum in `src/ruff_sync/constants.py`:

```python
class OutputFormat(str, enum.Enum):
    TEXT = "text"
    JSON = "json"
    GITHUB = "github"
    GITLAB = "gitlab"   # NEW
```

Update `get_formatter` in `formatters.py`:

```python
def get_formatter(output_format: OutputFormat) -> ResultFormatter:
    match output_format:
        case OutputFormat.GITHUB:
            return GithubFormatter()
        case OutputFormat.JSON:
            return JsonFormatter()
        case OutputFormat.GITLAB:
            return GitlabFormatter()
        case OutputFormat.TEXT:
            return TextFormatter()
```

---

## 8. Complete End-to-End Example Output

For a drift scenario where `lint.select` differs:

**`gl-code-quality-report.json`** (written to stdout, redirected to file):

```json
[
  {
    "description": "Config drift detected in pyproject.toml: 'lint.select' differs from upstream",
    "check_name": "ruff-sync/config-drift",
    "fingerprint": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
    "severity": "major",
    "location": {
      "path": "pyproject.toml",
      "lines": {
        "begin": 1
      }
    }
  }
]
```

**No drift** (in-sync):

```json
[]
```

---

## 9. Common Gotchas and Edge Cases

### 9.1 File Must Be Valid JSON — No Trailing Commas, No Comments

The file must be parseable by `json.dumps`/`json.loads`. Python's `json` module is fine.
Do NOT use TOML-style comments or trailing commas.

### 9.2 No BOM (Byte Order Mark)

GitLab's parser **rejects files with a BOM** at the start. Python's `json.dumps` does not add a
BOM, so this is not a concern as long as you use `str.encode()` or `pathlib.Path.write_text()`
without `encoding='utf-8-sig'`.

### 9.3 Path Must Be Relative to the Repository Root

`location.path` must be **relative** (e.g., `pyproject.toml`, `subdir/ruff.toml`). Absolute
paths will NOT create diff annotations — GitLab won't be able to match the file in the repo tree.

If the user runs `ruff-sync check` from a subdirectory, you need to output the path relative to
the repo root, not the working directory.

### 9.4 `begin: 1` Is Acceptable When Exact Line Is Unknown

ruff-sync compares entire config sections, not individual lines. Using `begin: 1` (the file's
first line) is acceptable and commonly done by tools that don't have line-level granularity.
GitLab will show the annotation at line 1 of the file.

### 9.5 Fingerprint Stability — Avoid Including Timestamps or Dynamic Data

Never include `datetime.now()`, UUIDs, or any runtime-variable data in the fingerprint input.
This would cause every run to report the same issue as "newly introduced."

### 9.6 MR Widget Only Shows Delta (Introduced vs. Fixed)

The merge request widget compares the report from the **MR branch** against the report from the
**target branch**. If you want "introduced" and "fixed" tracking to work correctly, the same
job must run on both branches with the same fingerprints.

### 9.7 Empty File vs. Missing File

- **Empty JSON array `[]`**: Correct. Means no issues. Previously reported issues are resolved.
- **Missing file**: GitLab silently ignores the missing artifact. Previous issues remain.
- **Invalid JSON**: GitLab may silently ignore or log a parsing error. Causes issues to remain.

Always write the file, even on error. In `ruff-sync`, use `try...finally` to ensure `finalize()`
is called even if an `UpstreamError` or other exception occurs.

### 9.8 The `|| true` Anti-Pattern

```yaml
# BAD — hides all exit codes, including real errors
script:
  - ruff-sync check --output-format gitlab > report.json || true
```

```yaml
# GOOD — job is still marked failed (for visibility), but artifact is uploaded
script:
  - ruff-sync check --output-format gitlab > report.json
artifacts:
  when: always
  reports:
    codequality: gl-code-quality-report.json
```

### 9.9 Tier Requirements for Full Feature Set

| Feature | Tier |
|---|---|
| MR widget (shows introduced/fixed count) | Free |
| MR changes view (inline diff annotations) | Ultimate |
| Pipeline Code Quality tab (full list) | Premium |
| Project quality view | Ultimate (Beta) |

On Free tier, `codequality` reports still work — they appear in the MR widget. The per-line diff
annotations require Ultimate.

### 9.10 Multiple Upstream Sources

If `ruff-sync check` compares against multiple upstreams, each upstream's drift should either:
- Be a **separate issue object** in the array (recommended for per-key granularity)
- Be **one issue per upstream** with a combined description

Use a different `check_name` per upstream if needed (e.g., `ruff-sync/upstream-1-drift`).

---

## 10. Integration with Existing `ruff-sync` Architecture

### What Needs to Change

| File | Change |
|---|---|
| `src/ruff_sync/constants.py` | Add `GITLAB = "gitlab"` to `OutputFormat` enum |
| `src/ruff_sync/formatters.py` | Add `GitlabFormatter` class; update `get_formatter` |
| `src/ruff_sync/cli.py` | Ensure `finalize()` is called after `check()` / `pull()` when format is `gitlab` |
| `.agents/skills/ruff-sync-usage/references/ci-integration.md` | Document `--output-format gitlab` |

### `finalize()` Call Site (in `cli.py`)

The `check()` and `pull()` coroutines must ensure `finalize()` is called. Use `try...finally`:

```python
fmt = get_formatter(exec_args.output_format)
try:
    exit_code = await check(exec_args, fmt=fmt)
finally:
    if hasattr(fmt, "finalize"):
        fmt.finalize()   # Writes the JSON array to stdout (piped to file by CI)
```

Or, more explicitly, check for `GitlabFormatter`:

```python
if isinstance(fmt, GitlabFormatter):
    fmt.finalize()
```

### Exit Codes (Unchanged)

The `GitlabFormatter` does not change exit codes. Exit codes remain:

| Code | Meaning |
|---|---|
| 0 | In sync |
| 1 | Config drift detected |
| 3 | Pre-commit hook drift |
| 4 | Upstream unreachable |

The CI job uses `when: always` to upload the artifact regardless of exit code.

---

## 11. Testing the GitlabFormatter

Add tests in `tests/test_basic.py` or a new `tests/test_formatters.py`:

```python
import json
import pathlib
from io import StringIO
from unittest.mock import patch

from ruff_sync.formatters import GitlabFormatter

def test_gitlab_formatter_empty_on_no_issues(capsys):
    fmt = GitlabFormatter()
    fmt.finalize()
    captured = capsys.readouterr()
    issues = json.loads(captured.out)
    assert issues == []

def test_gitlab_formatter_error_produces_major_issue(capsys):
    fmt = GitlabFormatter()
    fmt.error("drift found", file_path=pathlib.Path("pyproject.toml"))
    fmt.finalize()
    captured = capsys.readouterr()
    issues = json.loads(captured.out)
    assert len(issues) == 1
    assert issues[0]["severity"] == "major"
    assert issues[0]["location"]["path"] == "pyproject.toml"
    assert issues[0]["location"]["lines"]["begin"] == 1
    assert "fingerprint" in issues[0]

def test_gitlab_formatter_fingerprint_is_stable(capsys):
    fmt1 = GitlabFormatter()
    fmt2 = GitlabFormatter()
    fmt1.error("drift found", file_path=pathlib.Path("pyproject.toml"))
    fmt2.error("drift found", file_path=pathlib.Path("pyproject.toml"))
    fmt1.finalize()
    out1 = capsys.readouterr().out
    fmt2.finalize()
    out2 = capsys.readouterr().out
    issues1 = json.loads(out1)
    issues2 = json.loads(out2)
    assert issues1[0]["fingerprint"] == issues2[0]["fingerprint"]

def test_gitlab_formatter_no_bom(capsys):
    fmt = GitlabFormatter()
    fmt.finalize()
    captured = capsys.readouterr()
    assert not captured.out.startswith("\ufeff")
```

---

## 12. References

- [GitLab artifacts reports types](https://docs.gitlab.com/ci/yaml/artifacts_reports/)
- [GitLab Code Quality](https://docs.gitlab.com/ci/testing/code_quality/)
- [CodeClimate report spec (SPEC.md)](https://github.com/codeclimate/platform/blob/master/spec/analyzers/SPEC.md#data-types)
- [Ruff GitLab CI integration](https://docs.astral.sh/ruff/integrations/#gitlab-cicd)
- [ruff-sync existing formatters](../src/ruff_sync/formatters.py)
- [ruff-sync OutputFormat enum](../src/ruff_sync/constants.py)
- [ruff-sync Issue #102 context](../ISSUE_102_CONTEXT.md)
