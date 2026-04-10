# Refactoring Plan: Clean Up `strict` / `validate` / `pre_commit` Default Handling

> **Context**: Commit `051ca28` ("low effort handling of strict/validate defaults") changed the
> `Arguments` NamedTuple to use `bool | MissingType` for `validate`, `strict`, and `pre_commit`,
> then forced every consumer (`pull`, `check`, `_merge_multiple_upstreams`) to call
> `resolve_defaults()` at the top of the function and destructure a 6-tuple. This is architecturally
> bad for several reasons outlined below.

---

## Problem Analysis

### What the commit did

1. Changed `Arguments.validate`, `Arguments.strict`, and `Arguments.pre_commit` from `bool` to
   `bool | MissingType`.
2. Expanded `resolve_defaults()` from `(branch, path, exclude) → 3-tuple` to
   `(branch, path, exclude, validate, strict, pre_commit) → 6-tuple`, mixing two concerns (URL
   resolution defaults and boolean flag defaults).
3. Added `resolve_defaults()` calls to the top of `pull()`, `check()`, and
   `_merge_multiple_upstreams()`, each destructuring the 6-tuple with throw-away `_` variables.
4. Added `pre_commit` to `ResolvedArgs`, making it carry `bool | MissingType` too.

### Why this is bad

| Issue | Explanation |
|-------|-------------|
| **Sentinel leaks into execution logic** | `pull()` and `check()` don't care about `MISSING`—they just need a `bool`. But now their type signatures lie: `args.validate` is `bool \| MissingType`, so every access site needs a guard or a `resolve_defaults()` wrapper. |
| **Duplicated resolution** | `resolve_defaults()` is called 3 times (in `pull`, `check`, `_merge_multiple_upstreams`) with the same args. Each call independently resolves the same values. |
| **Bloated `resolve_defaults()`** | This function's original purpose was URL parameter defaults (branch, path, exclude). Boolean flags have nothing to do with URL resolution—they were bolted on. |
| **6-tuple destructuring** | `(branch, path, exclude, validate, strict, pre_commit) = resolve_defaults(...)` is fragile and unreadable. Adding one more field breaks every call site. |
| **Two representations, unclear boundary** | `Arguments` now holds `MISSING` values, but the CLI layer already resolved them in `_resolve_validate()` / `_resolve_strict()`. So `MISSING` can appear in `Arguments` from two sources: (a) the CLI resolver returned it, or (b) direct construction in tests. The semantics are unclear. |

### The real requirement

The `MISSING` sentinel is needed for **serialization only** (`serialize_ruff_sync_config`): when
`--save` is used, we must distinguish "user explicitly passed `--no-strict`" (serialize
`strict = false`) from "user said nothing about strict" (don't serialize the key at all). Execution
logic (`pull`, `check`) just needs a plain `bool`.

---

## Proposed Design

**Core idea**: Separate the _transport/serialization_ concern (`MISSING` awareness) from the
_execution_ concern (plain bools).

### Layer 1: `Arguments` (transport + serialization)

Keep `bool | MissingType` for `validate`, `strict`, and `pre_commit` here. This is the type that
`serialize_ruff_sync_config()` consumes. It is constructed _once_ in `main()` and passed to
`serialize_ruff_sync_config()` via `pull()`.

### Layer 2: `ExecutionArgs` (new NamedTuple — execution logic)

A **new** NamedTuple with **only plain `bool`** for `validate`, `strict`, and `pre_commit`. This is
what `pull()` and `check()` (and `_merge_multiple_upstreams`) actually use for control flow. It is
derived from `Arguments` via a single call to a new `Arguments.resolve()` method (or a standalone
`resolve_execution_args()` function).

```
CLI (argparse) ──► _resolve_args() ──► main() builds Arguments
                                            │
                        ┌───────────────────┤
                        ▼                   ▼
              serialize_ruff_sync_config  Arguments.resolve()
              (reads MISSING to decide     ──► ExecutionArgs
               what to serialize)              (plain bools)
                                               │
                                    ┌──────────┼──────────┐
                                    ▼          ▼          ▼
                                  pull()    check()   _merge_multiple_upstreams()
```

---

## Step-by-Step Implementation

### Step 1: Create `ExecutionArgs` NamedTuple

**File**: `src/ruff_sync/cli.py`

Add a new NamedTuple right after the existing `Arguments` class:

```python
class ExecutionArgs(NamedTuple):
    """Resolved arguments for execution logic — all sentinels replaced with concrete values."""

    command: str
    upstream: tuple[URL, ...]
    to: pathlib.Path
    exclude: Iterable[str]
    verbose: int
    branch: str
    path: str | None
    semantic: bool
    diff: bool
    init: bool
    pre_commit: bool      # plain bool — MISSING resolved to default
    save: bool | None
    output_format: OutputFormat
    validate: bool        # plain bool — MISSING resolved to default
    strict: bool          # plain bool — MISSING resolved to default
```

> [!NOTE]
> `save` stays `bool | None` because `None` has meaningful semantics there (trigger
> from `--init`), and it's already resolved before execution.

### Step 2: Add a `resolve()` method to `Arguments`

**File**: `src/ruff_sync/cli.py`

Add a method to `Arguments` that produces an `ExecutionArgs`:

```python
class Arguments(NamedTuple):
    # ... existing fields unchanged ...

    def resolve(self) -> ExecutionArgs:
        """Resolve all MISSING sentinels to their effective defaults for execution."""
        _, _, _, eff_validate, eff_strict, eff_pre_commit = resolve_defaults(
            MISSING,   # branch — already resolved, pass MISSING to skip
            MISSING,   # path — already resolved, pass MISSING to skip
            MISSING,   # exclude — already resolved, pass MISSING to skip
            self.validate,
            self.strict,
            self.pre_commit,
        )
        return ExecutionArgs(
            command=self.command,
            upstream=self.upstream,
            to=self.to,
            exclude=self.exclude,
            verbose=self.verbose,
            branch=self.branch,
            path=self.path,
            semantic=self.semantic,
            diff=self.diff,
            init=self.init,
            pre_commit=eff_pre_commit,
            save=self.save,
            output_format=self.output_format,
            validate=eff_validate,
            strict=eff_strict,
        )
```

> [!IMPORTANT]
> We still use `resolve_defaults()` for the boolean resolution logic (strict implies
> validate, defaults), but only call it **once** and only for the boolean fields.

### Step 3: Restore `resolve_defaults()` to its original scope

**File**: `src/ruff_sync/constants.py`

Revert `resolve_defaults()` to its original 3-parameter, 3-return form for URL parameter defaults.
Extract boolean resolution into a separate function:

```python
def resolve_defaults(
    branch: str | MissingType,
    path: str | None | MissingType,
    exclude: Iterable[str] | MissingType,
) -> tuple[str, str | None, Iterable[str]]:
    """Resolve MISSING sentinel values to their effective defaults.

    This is the single source of truth for MISSING → default resolution for
    URL-related parameters (branch, path, exclude).
    """
    eff_branch = branch if branch is not MISSING else DEFAULT_BRANCH
    raw_path = path if path is not MISSING else DEFAULT_PATH
    eff_path: str | None = raw_path or None
    eff_exclude = exclude if exclude is not MISSING else DEFAULT_EXCLUDE
    return eff_branch, eff_path, eff_exclude


def resolve_bool_flags(
    validate: bool | MissingType = MISSING,
    strict: bool | MissingType = MISSING,
    pre_commit: bool | MissingType = MISSING,
) -> tuple[bool, bool, bool]:
    """Resolve MISSING sentinel values for boolean execution flags.

    Returns:
        A ``(validate, strict, pre_commit)`` tuple with defaults applied.
        ``strict=True`` implicitly enables ``validate``.
    """
    eff_strict = strict if strict is not MISSING else False
    eff_validate = (validate if validate is not MISSING else False) or eff_strict
    eff_pre_commit = pre_commit if pre_commit is not MISSING else True
    return eff_validate, eff_strict, eff_pre_commit
```

> [!TIP]
> This is a clean separation: `resolve_defaults` handles URL stuff, `resolve_bool_flags`
> handles boolean stuff. Neither grows unbounded.

### Step 4: Update `Arguments.resolve()` to use `resolve_bool_flags`

**File**: `src/ruff_sync/cli.py`

Replace the `resolve_defaults()` call in `Arguments.resolve()` with `resolve_bool_flags()`:

```python
from ruff_sync.constants import resolve_bool_flags

class Arguments(NamedTuple):
    # ...
    def resolve(self) -> ExecutionArgs:
        eff_validate, eff_strict, eff_pre_commit = resolve_bool_flags(
            self.validate, self.strict, self.pre_commit,
        )
        return ExecutionArgs(
            command=self.command,
            upstream=self.upstream,
            to=self.to,
            exclude=self.exclude,
            verbose=self.verbose,
            branch=self.branch,
            path=self.path,
            semantic=self.semantic,
            diff=self.diff,
            init=self.init,
            pre_commit=eff_pre_commit,
            save=self.save,
            output_format=self.output_format,
            validate=eff_validate,
            strict=eff_strict,
        )
```

### Step 5: Update `pull()` to use `ExecutionArgs`

**File**: `src/ruff_sync/core.py`

Remove the `resolve_defaults()` call at the top of `pull()`. Instead, accept
**both** `Arguments` (for serialization) and call `.resolve()` once at the top:

```python
async def pull(args: Arguments) -> int:
    exec_args = args.resolve()   # single resolution point

    # Use exec.validate, exec.strict, exec.pre_commit for logic
    # Use args (original, with MISSING) only for serialize_ruff_sync_config()

    ...
    if exec.validate:
        ...validate_merged_config(..., strict=exec.strict, exclude=exec.exclude)

    ...
    if should_save:
        serialize_ruff_sync_config(source_doc, args)  # ← still uses raw args

    ...
    if exec.pre_commit:
        sync_pre_commit(...)
```

> [!WARNING]
> `serialize_ruff_sync_config()` **must** still receive the original `Arguments` (with
> `MISSING`) so it knows which flags to write and which to omit. Do NOT pass `ExecutionArgs` here.

### Step 6: Update `check()` to use `ExecutionArgs`

**File**: `src/ruff_sync/core.py`

Same pattern: call `args.resolve()` once, use the result for execution:

```python
async def check(args: Arguments) -> int:
    exec_args = args.resolve()

    ...
    exit_code = _check_pre_commit_sync(exec.pre_commit, fmt)
    ...
```

Remove the `resolve_defaults()` call and the 6-tuple destructuring.

### Step 7: Update `_merge_multiple_upstreams()`

**File**: `src/ruff_sync/core.py`

This function currently calls `resolve_defaults()` to get `branch`, `path`, and `exclude`. Since
these are already resolved by the time they reach `Arguments` (the CLI layer resolves them), the
call is actually redundant. However, if the function is also used by code that passes un-resolved
`Arguments`, we should change its signature to accept `ExecutionArgs` instead:

```python
async def _merge_multiple_upstreams(
    target_doc: TOMLDocument,
    is_target_ruff_toml: bool,
    args: ExecutionArgs,     # ← changed from Arguments
    client: httpx.AsyncClient,
) -> TOMLDocument:
    # No resolve_defaults() needed — args already has plain values
    fetch_results = await fetch_upstreams_concurrently(
        args.upstream, client, branch=args.branch, path=args.path
    )
    ...
```

> [!NOTE]
> Look at call sites: `_merge_multiple_upstreams` is called from both `pull()` and `check()`.
> Both will now pass `exec` (the `ExecutionArgs`) instead of raw `args`.

### Step 8: Remove `resolve_defaults` import from `core.py`

**File**: `src/ruff_sync/core.py`

After steps 5–7, `core.py` no longer needs `resolve_defaults` or `MISSING` from constants (unless
other code in the module still uses them). Clean up the imports.

### Step 9: Clean up `ResolvedArgs`

**File**: `src/ruff_sync/cli.py`

The `ResolvedArgs` NamedTuple was expanded to include `validate: bool | MissingType`,
`strict: bool | MissingType`, and `pre_commit: bool | MissingType`. These should be reverted to
exclude the boolean flags. `ResolvedArgs` is only used inside `_resolve_args()` → `main()`, and
the boolean flags are already individually resolved by `_resolve_validate()` and `_resolve_strict()`.

Two options:

- **Option A (recommended)**: Remove `validate`, `strict`, `pre_commit` from `ResolvedArgs`.
  Put them back onto `Arguments` directly in `main()` using the existing `_resolve_*` functions
  (which already return `bool | MissingType`).

- **Option B**: Leave `ResolvedArgs` as-is but document that its purpose is to shuttle values
  between `_resolve_args()` and `main()`.

With **Option A**, `main()` becomes:

```python
resolved = _resolve_args(args, config, initial_to)  # no validate/strict/pre_commit

exec_args = Arguments(
    ...
    validate=_resolve_validate(args, config),
    strict=_resolve_strict(args, config),
    pre_commit=_resolve_pre_commit(args, config),
    ...
)
```

### Step 10: Update tests

**File**: `tests/test_constants.py`

Revert `resolve_defaults` tests to the original 3-tuple assertions:

```python
def test_resolve_defaults_all_missing():
    branch, path, exclude = resolve_defaults(MISSING, MISSING, MISSING)
    assert branch == DEFAULT_BRANCH
    assert path is None
    assert exclude == DEFAULT_EXCLUDE
```

Add **new** tests for `resolve_bool_flags()`:

```python
from ruff_sync.constants import resolve_bool_flags

def test_resolve_bool_flags_all_missing():
    validate, strict, pre_commit = resolve_bool_flags(MISSING, MISSING, MISSING)
    assert validate is False
    assert strict is False
    assert pre_commit is True

def test_resolve_bool_flags_strict_implies_validate():
    validate, strict, pre_commit = resolve_bool_flags(MISSING, True, MISSING)
    assert validate is True
    assert strict is True

def test_resolve_bool_flags_explicit_false():
    validate, strict, pre_commit = resolve_bool_flags(False, False, False)
    assert validate is False
    assert strict is False
    assert pre_commit is False
```

**File**: `tests/test_serialization.py`

No changes needed — these tests construct `Arguments` with `MISSING` and pass to
`serialize_ruff_sync_config()`, which still consumes raw `Arguments`.

**File**: `tests/test_config_validation.py`

Update tests that currently destructure 6-tuples from `resolve_defaults()` to use the new API. Tests
for `pull()` and `check()` already pass `Arguments` objects, so they should work unchanged.

### Step 11: Run full validation

```bash
uv run ruff check . --fix
uv run ruff format .
uv run mypy .
uv run pytest -vv
```

---

## Summary of Changes

| File | Change |
|------|--------|
| `src/ruff_sync/constants.py` | Revert `resolve_defaults` to 3-param/3-return. Add `resolve_bool_flags()`. |
| `src/ruff_sync/cli.py` | Add `ExecutionArgs` NamedTuple. Add `Arguments.resolve()` method. Clean up `ResolvedArgs`. |
| `src/ruff_sync/core.py` | Replace `resolve_defaults()` calls in `pull`/`check`/`_merge_multiple_upstreams` with `args.resolve()`. Remove `MISSING`/`resolve_defaults` imports. |
| `tests/test_constants.py` | Revert to 3-tuple tests. Add `resolve_bool_flags` tests. |
| `tests/test_config_validation.py` | Minor updates if any test directly calls `resolve_defaults` with 6 args. |

### What does NOT change

- `Arguments` field types stay `bool | MissingType` for `validate`, `strict`, `pre_commit` (needed for serialization).
- `serialize_ruff_sync_config()` is unchanged — it still reads `MISSING` from `Arguments`.
- `_resolve_validate()`, `_resolve_strict()`, `_resolve_pre_commit()` in `cli.py` are unchanged.
- CLI argument parser is unchanged.

### Architecture benefit

```
Before (051ca28):
  Arguments (MISSING everywhere) ──► resolve_defaults() called 3× in core.py

After (this refactor):
  Arguments (MISSING for serialize) ──► .resolve() ──► ExecutionArgs (plain bools) ──► core logic
                                           ↑ called ONCE
```

The sentinel is contained to the serialization boundary. Execution logic gets clean types.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Changing `_merge_multiple_upstreams` signature breaks internal callers | It's a private function with only 2 call sites (`pull`, `check`). Both are updated in the same PR. |
| `ExecutionArgs` adds another NamedTuple | It replaces the ad-hoc 6-tuple destructuring, which is worse. The NamedTuple is self-documenting and type-safe. |
| Tests that construct `Arguments` directly need `MISSING` for new defaults | Already the case — no change. |
