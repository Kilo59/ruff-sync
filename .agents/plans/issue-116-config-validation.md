# Implementation Plan: Config Validation (Issue #116)

> **GitHub Issue**: [Feature Roadmap: Config Validation #116](https://github.com/Kilo59/ruff-sync/issues/116)
> **Parent Roadmap**: [#100](https://github.com/Kilo59/ruff-sync/issues/100) (Item #10)
>
> When running `ruff-sync pull`, validating the merged configuration before applying it ensures
> that we don't introduce syntax errors, conflicting versions, or deprecated rules into the
> target repository.

## Design Decision: Validation is Opt-In

Validation is **not run by default**. Users must explicitly request it via `--validate`.
This avoids adding latency (a subprocess `ruff check` invocation) and an implicit dependency
on `ruff` being available in the shell environment to every `pull` invocation.

`--strict` implies `--validate`. Passing `--strict` without `--validate` is equivalent to
passing both.

---

## Overview of Priorities

> **Complexity scale**: 🟢 Simple → 🟡 Moderate → 🔴 Complex
> Use this to pick your agent tier. Simple phases can be handled by a weak/cheap model;
> Complex phases need a capable reasoning model.

| Priority | Label | Complexity | Feature | Scope | Status |
|---|---|---|---|---|---|
| 1 (Must Have) | 🔴 | 🟡 Moderate | TOML syntax + Ruff CLI validation | New `validation.py` module; gated by `--validate` in `pull()` | ✅ Completed |
| 2 (Should Have) | 🟠 | 🟢 Simple | Python version consistency check | `validation.py` + warn when `--validate` is active | ✅ Completed |
| 3 (Could Have) | 🟡 | 🔴 Complex | Rule deprecation warnings | `validation.py` + subprocess + JSON + DI; gated by `--validate` | ⏳ Pending |
| 4 (Nice to Have) | 🟢 | 🟢 Simple | `--strict` flag | Upgrades warnings to failures; implies `--validate` | 🚧 In Progress |

---

## Priority 1 — TOML Syntax + Ruff CLI Validation `🟡 Moderate`

> **Why Moderate**: Requires creating a new module from scratch, understanding Ruff subprocess
> exit-code semantics (0/1 vs 2), implementing soft-fail behaviour, **and** wiring three files
> (`validation.py`, `cli.py`, `core.py`) all in one phase. Any one piece alone would be Simple;
> the cross-file coordination bumps it to Moderate.

### What it does

Before writing the merged `pyproject.toml` (or `ruff.toml`) back to disk, ruff-sync should:

1. Verify the merged document is still valid TOML (it always should be since `tomlkit` builds it,
   but this is a belt-and-suspenders check).
2. Write the merged content to a **temporary file** and run
   `ruff check --isolated --config <tmp> <dummy-py-file>` to confirm Ruff accepts the config.
3. If Ruff rejects the config, **abort** — log an error and leave the local file untouched.

### Step-by-step implementation

#### Step 1 — Create `src/ruff_sync/validation.py`

Create a new file `src/ruff_sync/validation.py`. It needs:

```python
from __future__ import annotations
```

Imports to include (follow project conventions — no `from pathlib import Path`):

```python
import logging
import pathlib
import subprocess
import tempfile

from tomlkit import TOMLDocument
```

Add a module-level logger:

```python
LOGGER = logging.getLogger(__name__)
```

##### Function 1: `validate_toml_syntax`

```python
def validate_toml_syntax(doc: TOMLDocument) -> bool:
    """Return True if the document serializes to valid TOML.

    tomlkit always produces valid TOML, so this catches any edge cases
    where serialization itself raises an unexpected exception.
    """
    try:
        import tomlkit  # already a dep
        tomlkit.parse(doc.as_string())
        return True
    except Exception:  # noqa: BLE001
        LOGGER.error("❌ Merged config failed TOML syntax check.")
        return False
```

> **Note**: `tomlkit.parse` is used (not just `doc.as_string()`) so we exercise the full
> round-trip and catch any serialization anomalies.

##### Function 2: `validate_ruff_accepts_config`

This is the main validation function. It writes the merged doc to a temp file and invokes Ruff.

```python
def validate_ruff_accepts_config(doc: TOMLDocument, is_ruff_toml: bool = False) -> bool:
    """Return True if Ruff accepts the merged configuration.

    Writes the merged config to a temporary file and runs:
        ruff check --isolated --config <tmp> <dummy-py-file>

    Args:
        doc: The merged TOML document to validate.
        is_ruff_toml: True if the document is a ruff.toml (not pyproject.toml).

    Returns:
        True if Ruff accepts the config without errors, False otherwise.
    """
    suffix = ".toml" if is_ruff_toml else "_pyproject.toml"
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir) / f"ruff_config{suffix}"
        tmp_path.write_text(doc.as_string(), encoding="utf-8")

        # Create a minimal dummy Python file for ruff to lint
        dummy_py = pathlib.Path(tmp_dir) / "dummy.py"
        dummy_py.write_text("# ruff-sync config validation\n", encoding="utf-8")

        config_flag = f"--config={tmp_path}"
        cmd = ["ruff", "check", "--isolated", config_flag, str(dummy_py)]
        LOGGER.debug(f"Running ruff config validation: {' '.join(cmd)}")

        try:
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 or result.returncode == 1:
                # Exit 0 = no issues found, exit 1 = issues found — both mean ruff
                # parsed the config successfully. Exit 2 = config/usage error.
                return True
            LOGGER.error(
                f"❌ Ruff rejected the merged config (exit {result.returncode}):\n"
                f"{result.stderr.strip()}"
            )
            return False
        except FileNotFoundError:
            LOGGER.warning(
                "⚠️  `ruff` not found on PATH — skipping Ruff config validation."
            )
            return True  # Soft fail: don't block if ruff isn't installed
        except subprocess.TimeoutExpired:
            LOGGER.warning("⚠️  Ruff config validation timed out — skipping.")
            return True  # Soft fail on timeout
```

> **Important**: Ruff exit code `1` means "linting issues found" (not a config error). Only
> exit code `2` (or higher) means the config itself is broken. We treat 0 and 1 as success.

##### Function 3 (public entrypoint): `validate_merged_config`

```python
def validate_merged_config(doc: TOMLDocument, is_ruff_toml: bool = False) -> bool:
    """Run all validation checks on the merged TOML document.

    Returns True only if all checks pass. Returns False and logs errors
    if any check fails.
    """
    if not validate_toml_syntax(doc):
        return False
    if not validate_ruff_accepts_config(doc, is_ruff_toml=is_ruff_toml):
        return False
    return True
```

#### Step 2 — Add `--validate` flag and `validate` field to `cli.py`

Validation is **opt-in**. Before touching `core.py`, wire up the CLI flag.

**In `Arguments` (NamedTuple, around line 95)**, add two new fields after the existing ones:

```python
class Arguments(NamedTuple):
    ...
    validate: bool = False  # run --validate checks before writing
    strict: bool = False    # treat warnings as errors (implies validate)
```

**In `common_parser`** (around line 236), add:

```python
common_parser.add_argument(
    "--validate",
    action="store_true",
    default=False,
    help=(
        "Validate the merged config with Ruff before writing to disk. "
        "Aborts if Ruff rejects the config. Off by default."
    ),
)
```

**In `main()`**, in the `exec_args = Arguments(...)` block add:

```python
exec_args = Arguments(
    ...
    validate=getattr(args, "validate", False) or getattr(args, "strict", False),
    strict=getattr(args, "strict", False),
)
```

> `validate` is forced `True` when `strict` is `True` — strict is a superset of validate.

#### Step 3 — Hook validation into `pull()` in `src/ruff_sync/core.py`

Open `core.py`. Find the `pull()` function (around line 1103). Look for this block:

```python
        async with httpx.AsyncClient() as client:
            source_doc = await _merge_multiple_upstreams(
                source_doc,
                is_target_ruff_toml=is_ruff_toml_file(_source_toml_path.name),
                args=args,
                client=client,
            )
```

**After** this block (and **before** `should_save = args.save ...`), insert:

```python
        # Validation is opt-in — only run if --validate (or --strict) was passed
        if args.validate:
            is_ruff_toml = is_ruff_toml_file(_source_toml_path.name)
            from ruff_sync.validation import validate_merged_config  # noqa: PLC0415
            if not validate_merged_config(
                source_doc, is_ruff_toml=is_ruff_toml, strict=args.strict
            ):
                fmt.error(
                    "❌ Merged config failed validation. Local file left unchanged.",
                    logger=LOGGER,
                )
                return 1
```

> **Note**: The inline import avoids a circular import issue if `validation.py` ever needs to
> import from `core.py` in the future. Place it at the top of the file under `TYPE_CHECKING`
> once you've confirmed there's no circular dependency.

#### Step 4 — Export from `__init__.py`

Open `src/ruff_sync/__init__.py`. Add `validate_merged_config` to `__all__` if it is public.
Check the current `__all__` list first and follow the existing alphabetical pattern.

#### Step 5 — Add tests in `tests/test_config_validation.py`

> There is already a `tests/test_config_validation.py` file. **Open it first and read what's
> already there** before adding tests, to avoid duplicates.

Tests to add:

1. **`test_validate_toml_syntax_valid`** — pass a valid `TOMLDocument`, assert `True`.
2. **`test_validate_ruff_accepts_config_valid`** — pass a minimal valid ruff config, assert `True`.
3. **`test_validate_ruff_accepts_config_invalid`** — pass a config with a bogus key
   (e.g., `not-a-real-key = "boom"`), assert `False`.
4. **`test_validate_merged_config_returns_false_on_invalid`** — same as #3 but via the
   top-level `validate_merged_config` entrypoint.
5. **`test_pull_aborts_on_invalid_config`** — integration-style test using `pyfakefs` +
   `respx` that asserts the local file is **not modified** when validation fails.
   - Build `Arguments` with `validate=True`.
   - Use `respx.mock` to return an upstream config containing a deliberately invalid Ruff key.
   - Assert the return code from `pull(args)` is `1`.
   - Assert the local `pyproject.toml` content is unchanged.

6. **`test_pull_skips_validation_by_default`** — same setup but `validate=False` (default).
   - Assert the return code is `0` (pull succeeds even with a bad upstream key, because validation
     was not requested).
   - This is the regression guard ensuring validation is truly opt-in.

**Test patterns to follow** (from project conventions):

- Use `@pytest.mark.asyncio` for async tests.
- Use `pyfakefs` fixture (`fs`) for filesystem mocking; NOT `tmpdir` or `monkeypatch`.
- Use `respx` for HTTP mocking; NOT `unittest.mock`.
- Add `from __future__ import annotations` as the very first line.
- Use `import pathlib` (not `from pathlib import Path`).
- Do NOT use `autouse=True` on any fixture.

Example skeleton (adapt as needed):

```python
from __future__ import annotations

import pathlib

import pytest
import tomlkit

from ruff_sync.validation import validate_merged_config, validate_toml_syntax


def test_validate_toml_syntax_valid() -> None:
    doc = tomlkit.parse("[tool.ruff]\nline-length = 100\n")
    assert validate_toml_syntax(doc) is True


def test_validate_merged_config_invalid_ruff_key() -> None:
    doc = tomlkit.parse("[tool.ruff]\nnot-a-real-key = true\n")
    # This may return True if ruff is lenient; adjust based on actual ruff behavior.
    # The important thing is that the function completes without raising.
    result = validate_merged_config(doc)
    assert isinstance(result, bool)
```

> **️⚠️ Important caveat**: Ruff's leniency toward unknown keys varies by version. Run
> `ruff check --isolated --config <file-with-bogus-key> dummy.py` manually to see what Ruff
> actually does before writing the assertion. Adjust the test to match real behavior.

---

## Priority 2 — Python Version Consistency Check `🟢 Simple`

> **Why Simple**: Self-contained addition to an already-created module. Pure Python string
> parsing with regex — no subprocesses, no cross-file wiring. Warning-only (no abort logic).
> Tests use only `caplog` (built-in pytest fixture, nothing exotic).

### What it does

After merging, check if the `[tool.ruff] target-version` in the merged doc (e.g., `py311`)
is compatible with the local `[project] requires-python` (e.g., `>=3.10`). If they conflict,
**warn** the user but do not abort (this is a warning, not a hard failure).

### Ruff `target-version` values

Ruff uses strings like `"py38"`, `"py39"`, `"py310"`, `"py311"`, `"py312"`, `"py313"`.
They map to Python minor versions 3.8 through 3.13.

### Step-by-step implementation

#### Step 1 — Add `check_python_version_consistency` to `validation.py`

```python
import re

_RUFF_TARGET_VERSION_PATTERN = re.compile(r"^py(\d)(\d+)$")


def _ruff_target_to_tuple(target_version: str) -> tuple[int, int] | None:
    """Parse a Ruff target-version string (e.g. 'py311') into a (major, minor) tuple."""
    m = _RUFF_TARGET_VERSION_PATTERN.match(target_version)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _requires_python_min_version(requires_python: str) -> tuple[int, int] | None:
    """Extract the minimum Python version from a PEP 440 requires-python string.

    Examples:
        '>=3.10' -> (3, 10)
        '^3.11'  -> (3, 11)
        '~=3.9'  -> (3, 9)
    """
    # Match the first version specifier of the form X.Y
    m = re.search(r"(\d+)\.(\d+)", requires_python)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


def check_python_version_consistency(doc: TOMLDocument) -> None:
    """Warn if the merged ruff target-version conflicts with requires-python.

    This is a warning-only check. It does not return False or abort the sync.

    Args:
        doc: The merged TOML document (pyproject.toml format).
    """
    try:
        ruff_section = doc.get("tool", {}).get("ruff", {})
        target_version = ruff_section.get("target-version")
        requires_python = doc.get("project", {}).get("requires-python")
    except Exception:  # noqa: BLE001
        return  # Don't crash on unexpected doc shapes

    if not target_version or not requires_python:
        return  # Nothing to compare

    ruff_min = _ruff_target_to_tuple(str(target_version))
    proj_min = _requires_python_min_version(str(requires_python))

    if ruff_min is None or proj_min is None:
        return  # Couldn't parse one of the versions

    if ruff_min < proj_min:
        LOGGER.warning(
            f"⚠️  Version mismatch: upstream [tool.ruff] target-version='{target_version}' "
            f"targets Python {ruff_min[0]}.{ruff_min[1]}, but local [project] requires-python="
            f"'{requires_python}' requires Python >= {proj_min[0]}.{proj_min[1]}. "
            "Consider updating target-version in the upstream config."
        )
```

#### Step 2 — Call the version check inside `validate_merged_config`

Update `validate_merged_config` to call `check_python_version_consistency` (only for
`pyproject.toml`, not `ruff.toml`):

```python
def validate_merged_config(doc: TOMLDocument, is_ruff_toml: bool = False) -> bool:
    if not validate_toml_syntax(doc):
        return False
    if not validate_ruff_accepts_config(doc, is_ruff_toml=is_ruff_toml):
        return False
    if not is_ruff_toml:
        check_python_version_consistency(doc)
    return True
```

#### Step 3 — Tests for version consistency

Add to `tests/test_config_validation.py`:

1. **`test_version_consistency_warn_on_mismatch`** — build a doc where `target-version = "py311"`
   but `requires-python = ">=3.10"`. Capture log output and assert a `WARNING` was emitted.
   Use `caplog` fixture (built-in pytest fixture, not a mock).

2. **`test_version_consistency_no_warn_when_compatible`** — build a doc where both versions
   agree. Assert no warning was emitted.

3. **`test_version_consistency_skipped_for_ruff_toml`** — call `validate_merged_config` with
   `is_ruff_toml=True`. Assert no warning is emitted even if the version fields would conflict.

**How to capture log warnings in tests**:

```python
def test_version_consistency_warn_on_mismatch(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    doc = tomlkit.parse(
        '[project]\nrequires-python = ">=3.10"\n\n[tool.ruff]\ntarget-version = "py39"\n'
    )
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        check_python_version_consistency(doc)
    assert "Version mismatch" in caplog.text
```

---

## Priority 3 — Rule Deprecation Warnings `🔴 Complex`

> **Why Complex**: Requires a subprocess call to `ruff rule --all --output-format json` plus
> JSON parsing, `functools.lru_cache` for caching, **and** a dependency-injection refactor of
> `check_deprecated_rules` so tests don't invoke real subprocesses (the project forbids mocks).
> This is the step most likely to trip up a weak agent.

### What it does

After merging, check each rule ID in `[tool.ruff.lint]` fields `select`, `extend-select`,
and `ignore` against the list of rules that Ruff itself reports as deprecated. If any deprecated
rules are detected, emit a **warning** per rule (not a hard failure).

### How to get the deprecated rule list from Ruff

Run `ruff rule --all --output-format json` (or `ruff rule <RULE_CODE>` for individual checks).
Ruff outputs a JSON array of rule objects, each with a `deprecated` field.

> **Verify first**: Run `ruff rule --help` to see exact flags for your installed Ruff version.
> The JSON output format may vary. As of Ruff 0.15+, `ruff rule --all --output-format json`
> should work.

### Step-by-step implementation

#### Step 1 — Add `get_deprecated_rules` to `validation.py`

```python
import json


def _get_deprecated_rule_codes() -> frozenset[str]:
    """Return the set of deprecated rule codes reported by the installed Ruff version.

    Returns an empty frozenset if ruff is not found or output cannot be parsed.
    """
    try:
        result = subprocess.run(  # noqa: S603
            ["ruff", "rule", "--all", "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return frozenset()
        rules = json.loads(result.stdout)
        return frozenset(
            r["code"] for r in rules if r.get("deprecated") is True
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
        return frozenset()
```

> **Note**: Cache this result with `functools.lru_cache` to avoid re-invoking Ruff multiple
> times per session. Add `@functools.lru_cache(maxsize=1)` above the function definition
> and add `import functools` to the imports.

#### Step 2 — Add `check_deprecated_rules` to `validation.py`

```python
_RULE_LIST_KEYS: frozenset[str] = frozenset({"select", "extend-select", "ignore"})


def check_deprecated_rules(doc: TOMLDocument, is_ruff_toml: bool = False) -> None:
    """Warn if the merged config references any deprecated Ruff rules.

    Args:
        doc: The merged TOML document.
        is_ruff_toml: True if the document is a standalone ruff.toml.
    """
    deprecated_codes = _get_deprecated_rule_codes()
    if not deprecated_codes:
        return  # Nothing to check (ruff not found or returned no deprecated rules)

    if is_ruff_toml:
        lint_section = doc.get("lint", {})
    else:
        lint_section = doc.get("tool", {}).get("ruff", {}).get("lint", {})

    if not isinstance(lint_section, dict):
        return

    for key in _RULE_LIST_KEYS:
        rule_list = lint_section.get(key, [])
        if not isinstance(rule_list, list):
            continue
        for rule_code in rule_list:
            rule_str = str(rule_code).strip().upper()
            if rule_str in deprecated_codes:
                LOGGER.warning(
                    f"⚠️  Upstream config uses deprecated rule '{rule_str}' "
                    f"(found in [tool.ruff.lint].{key}). "
                    "This rule may be removed in a future Ruff version."
                )
```

#### Step 3 — Hook into `validate_merged_config`

```python
def validate_merged_config(doc: TOMLDocument, is_ruff_toml: bool = False) -> bool:
    if not validate_toml_syntax(doc):
        return False
    if not validate_ruff_accepts_config(doc, is_ruff_toml=is_ruff_toml):
        return False
    if not is_ruff_toml:
        check_python_version_consistency(doc)
    check_deprecated_rules(doc, is_ruff_toml=is_ruff_toml)
    return True
```

#### Step 4 — Tests for rule deprecation warnings

Add to `tests/test_config_validation.py`.

> ⚠️ **Do NOT call the real `ruff rule --all` in tests.** Use `pyfakefs` + a fake `subprocess`
> response. Since the project forbids `unittest.mock`, use dependency injection: refactor
> `_get_deprecated_rule_codes` to accept an optional `ruff_output` argument for testing, or
> inject the rule codes set via a parameter to `check_deprecated_rules`.

**Preferred approach — inject via parameter**:

```python
def check_deprecated_rules(
    doc: TOMLDocument,
    is_ruff_toml: bool = False,
    _deprecated_codes: frozenset[str] | None = None,
) -> None:
    deprecated_codes = _deprecated_codes if _deprecated_codes is not None else _get_deprecated_rule_codes()
    ...
```

Tests:

1. **`test_deprecated_rule_warning_emitted`** — call `check_deprecated_rules` with a doc
   containing `select = ["UP036"]` and `_deprecated_codes=frozenset({"UP036"})`. Assert warning
   logged.

2. **`test_no_warning_for_valid_rules`** — same but with `select = ["E501"]` (not deprecated).
   Assert no warning logged.

3. **`test_deprecated_rules_skipped_when_ruff_unavailable`** — pass `_deprecated_codes=frozenset()`
   (empty, simulating Ruff not found). Assert no warning logged.

---

## Priority 4 — `--strict` Flag `🟢 Simple`

> **Why Simple**: Both CLI flags (`--validate`, `--strict`) were already wired in P1. This
> phase is purely about updating `validate_merged_config` to return `False` instead of just
> logging a warning when `strict=True`. All scaffolding already exists.

### What it does

When `--strict` is passed to `ruff-sync pull`, any **warning** from Priorities 2 or 3
(version mismatch, deprecated rules) is upgraded to a **hard failure** (non-zero exit code)
and the sync is aborted.

`--strict` automatically implies `--validate`. You do not need to pass both.

### Step-by-step implementation

#### Step 1 — `--strict` and `--validate` CLI args are added together

Both `--validate` and `--strict` were already added to `Arguments` and the parser in
Priority 1 / Step 2. Refer back to that step — no additional CLI changes are needed here.

#### Step 2 — Use `strict` in `validate_merged_config`

Update `validate_merged_config` signature and behavior:

```python
def validate_merged_config(
    doc: TOMLDocument,
    is_ruff_toml: bool = False,
    strict: bool = False,
) -> bool:
    if not validate_toml_syntax(doc):
        return False
    if not validate_ruff_accepts_config(doc, is_ruff_toml=is_ruff_toml):
        return False

    # Version consistency — warn normally, fail in strict mode
    if not is_ruff_toml:
        version_ok = _check_python_version_consistency_strict(doc, strict=strict)
        if not version_ok:
            return False

    # Deprecated rules — warn normally, fail in strict mode
    deprecated_ok = _check_deprecated_rules_strict(doc, is_ruff_toml=is_ruff_toml, strict=strict)
    if not deprecated_ok:
        return False

    return True
```

> **Refactor note**: Split the warning-logging and return-value concerns in Priorities 2 & 3
> functions so they can optionally return `False` in strict mode instead of just logging.
> The simplest approach: make them return a `bool` (True = OK, False = problem found),
> and the caller decides whether to abort based on `strict`.

The call in `pull()` (added in Priority 1 / Step 3) already passes `strict=args.strict`.
No further change to `pull()` is needed.

#### Step 3 — Update `Config` TypedDict in `core.py` (if persisting flags)

If `--validate` / `--strict` should be saveable to `[tool.ruff-sync]`, add them to the
`Config` TypedDict and to `ConfKey` in `constants.py`. This is optional for a first
implementation.

#### Step 4 — Tests for `--strict`

Add to `tests/test_config_validation.py`:

1. **`test_strict_mode_fails_on_version_mismatch`** — call `validate_merged_config` with a
   version-mismatched doc and `strict=True`. Assert result is `False`.

2. **`test_non_strict_mode_passes_on_version_mismatch`** — same doc, `strict=False`. Assert
   result is `True` (warning is emitted but doesn't fail).

3. **`test_strict_mode_fails_on_deprecated_rules`** — call with a deprecated rule and
   `strict=True`. Assert `False`.

---

## File-by-file Change Summary

| File | Change Type | What changes |
|---|---|---|
| `src/ruff_sync/validation.py` | **NEW** | All validation logic |
| `src/ruff_sync/cli.py` | **MODIFY** | Add `validate: bool` + `strict: bool` to `Arguments`; add `--validate` + `--strict` to `common_parser`; thread both through `main()` (strict forces validate=True) |
| `src/ruff_sync/core.py` | **MODIFY** | Call `validate_merged_config` in `pull()` **only when** `args.validate` is `True` |
| `src/ruff_sync/constants.py` | **MODIFY** (optional) | Add `ConfKey.VALIDATE` / `ConfKey.STRICT` if persisting to `[tool.ruff-sync]` |
| `src/ruff_sync/__init__.py` | **MODIFY** | Export `validate_merged_config` |
| `tests/test_config_validation.py` | **MODIFY** | Add all new test cases listed above, including the regression test that confirms validation is skipped by default |

---

## Implementation Order (for a sequential agent)

Execute the steps in this exact order to avoid broken intermediate states:

1. Create `src/ruff_sync/validation.py` with `validate_toml_syntax`, `validate_ruff_accepts_config`,
   and `validate_merged_config` (Priority 1 only first).
2. Run `uv run ruff check . --fix` and `uv run ruff format .` — fix any issues.
3. Run `uv run mypy .` — fix any type errors.
4. Add `validate: bool = False` and `strict: bool = False` to `Arguments` in `cli.py`.
   Add `--validate` and `--strict` to `common_parser`. In `main()`, set
   `validate=args.validate or args.strict` and `strict=args.strict`.
5. Hook `validate_merged_config` into `pull()` in `core.py`, **guarded by `if args.validate:`**.
6. Run `uv run pytest -vv` — make sure existing tests still pass.
7. Add Priority 1 tests to `tests/test_config_validation.py`, including
   `test_pull_skips_validation_by_default` (the opt-in regression guard).
8. Run `uv run pytest tests/test_config_validation.py -vv` — make sure new tests pass.
9. Add `check_python_version_consistency` to `validation.py` (Priority 2).
10. Update `validate_merged_config` to call the version check.
11. Add Priority 2 tests. Run `uv run pytest -vv`.
12. Add `_get_deprecated_rule_codes` and `check_deprecated_rules` (Priority 3).
13. Update `validate_merged_config` to call the deprecation check.
14. Add Priority 3 tests. Run `uv run pytest -vv`.
15. Update `validate_merged_config` to respect `strict` for P2/P3 warnings (Priority 4).
16. Add Priority 4 tests. Run `uv run pytest -vv`.
17. Final full validation:
    ```bash
    uv run ruff check . --fix
    uv run ruff format .
    uv run mypy .
    uv run pytest -vv
    ```

---

## Key Constraints & Gotchas

- **Validation is opt-in**: The `pull()` guard is `if args.validate:`. Without `--validate`
  (or `--strict`), no validation subprocess is spawned and no `validation.py` code is executed.
  This must be verified by a dedicated regression test (`test_pull_skips_validation_by_default`).
- **`--strict` implies `--validate`**: In `main()`, resolve
  `validate = args.validate or args.strict`. Never require the user to pass both flags.
- **No `unittest.mock`**: Dependency injection is required for testability. Pass Ruff output
  (or deprecated code sets) as function arguments in test scenarios.
- **No `autouse=True`**: All test fixtures must be explicitly requested.
- **`import pathlib`**, not `from pathlib import Path`.
- **`from __future__ import annotations`** must be the first line in every new `.py` file.
- **`tomlkit` objects**: Use `.get()` with defaults to avoid `KeyError` on missing sections.
- **Ruff exit codes**: `0` = no lint issues, `1` = lint issues found, `2` = config/usage error.
  Only `2` (and above) should be treated as a config validation failure.
- **Ruff not on PATH**: `validate_ruff_accepts_config` must **soft-fail** (return `True` with a
  warning) if `ruff` is not found. Do not crash the user's sync because their environment lacks
  the binary on PATH.
- **`is_ruff_toml` flag**: Must be threaded throughout validation so functions look in the right
  table path (`[tool.ruff]` vs root for `ruff.toml`).
- **The local file must be left untouched on failure**: In `pull()`, do not call
  `source_toml_file.write(source_doc)` if `validate_merged_config` returns `False`.
