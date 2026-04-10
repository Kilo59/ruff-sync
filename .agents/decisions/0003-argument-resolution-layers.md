# ADR 0003: Two-Layer Argument Resolution (Transport vs Execution)

---
status: proposed
date: 2026-04-10
decider: User + Agent
---

## Context

`ruff-sync` uses a `MISSING` sentinel (`MissingType.SENTINEL`) throughout its configuration
system to distinguish between "the user explicitly set this value" and "the user said nothing."
This distinction is critical for **serialization**: when `--save` persists CLI arguments to
`[tool.ruff-sync]` in `pyproject.toml`, only explicitly-set values should be written. A field
left as `MISSING` means "don't touch this key in the TOML file."

The problem arises when `MISSING` leaks into **execution logic**. Functions like `pull()` and
`check()` need plain `bool` values to make control-flow decisions (`if validate:`, `if strict:`).
If these functions receive `bool | MissingType`, every access site needs a guard or a resolution
call, and the type system stops helping.

A prior attempt (commit `051ca28`) solved this by making `Arguments` carry `bool | MissingType`
for `validate`, `strict`, and `pre_commit`, then calling `resolve_defaults()` at the top of every
consumer function. This led to:

- **Triplicated resolution calls** in `pull()`, `check()`, and `_merge_multiple_upstreams()`.
- **Bloated `resolve_defaults()`** mixing unrelated concerns (URL params + boolean flags).
- **Fragile 6-tuple destructuring** at every call site.
- **Unclear ownership** of where sentinels are resolved.

## Decision

Argument handling uses **two distinct layers**:

### Layer 1: Transport / Serialization (`Arguments`)

`Arguments` is the NamedTuple constructed by `main()` after CLI parsing and config merging.
It carries `bool | MissingType` for fields where the _absence_ of a value is meaningful for
serialization (`validate`, `strict`, `pre_commit`).

- **Consumed by**: `serialize_ruff_sync_config()` (the `--save` path).
- **Rule**: Only `serialize_ruff_sync_config()` should inspect `MISSING` on these fields.

### Layer 2: Execution (`ExecutionArgs`)

`ExecutionArgs` is a separate NamedTuple with **only plain `bool`** for all boolean flags.
All `MISSING` sentinels are resolved to their concrete defaults (e.g., `strict` defaults to
`False`, `pre_commit` defaults to `True`, `strict=True` implies `validate=True`).

- **Produced by**: `Arguments.resolve()` — called **once** at the top of `pull()` / `check()`.
- **Consumed by**: All execution logic (`pull`, `check`, `_merge_multiple_upstreams`, `_check_pre_commit_sync`, `validate_merged_config`).
- **Rule**: Execution functions must never see `MissingType`.

### Resolution Functions

Default resolution is split by concern:

| Function | Scope | Returns |
|----------|-------|---------|
| `resolve_defaults(branch, path, exclude)` | URL-related parameters | `(str, str \| None, Iterable[str])` |
| `resolve_bool_flags(validate, strict, pre_commit)` | Boolean execution flags | `(bool, bool, bool)` |

Neither function should grow to absorb the other's concerns. If a new parameter category
emerges (e.g., output formatting defaults), it should get its own resolution function.

### Data Flow

```
CLI (argparse)
  │
  ▼
_resolve_args() + _resolve_validate/strict/pre_commit()
  │
  ▼
main() builds Arguments (MISSING-aware)
  │
  ├──► serialize_ruff_sync_config(args)   ← reads MISSING to decide what to write
  │
  └──► args.resolve() → ExecutionArgs     ← MISSING → concrete defaults
         │
         └──► pull() / check() / internal logic  ← plain bools only
```

## Consequences

### Easier

- **Type safety**: Execution functions have `bool` fields — no unions, no guards, no runtime
  ambiguity.
- **Single resolution point**: `MISSING` → default happens in exactly one place
  (`Arguments.resolve()`), not scattered across consumer functions.
- **Extensibility**: Adding a new boolean flag means adding it to both `Arguments` (with
  `MissingType`) and `ExecutionArgs` (with `bool`), plus a line in `resolve_bool_flags()`.
  No 6-tuple explosions.
- **Agent-friendliness**: The pattern is explicit and mechanical — hard to get wrong.

### Harder

- **Two NamedTuples to maintain**: Adding a new field requires updating both `Arguments` and
  `ExecutionArgs`. This is intentional friction — it forces the developer to think about whether
  the new field needs `MISSING` semantics.
- **`pull()` holds two references**: `args` (for serialization) and `exec` (for logic). This is
  a feature, not a bug — it makes the boundary visible.

### Rules for Future Changes

1. **Never pass `MissingType` to execution logic.** If a function's parameter is `bool`, it must
   receive `bool`. Use `Arguments.resolve()` to get `ExecutionArgs` first.
2. **Never call `resolve_defaults()` or `resolve_bool_flags()` inside `pull()` / `check()`.**
   Call `args.resolve()` once and pass the result down.
3. **`serialize_ruff_sync_config()` always receives raw `Arguments`**, never `ExecutionArgs`.
   It needs to see `MISSING` to know what to omit.
4. **Don't merge resolution functions.** `resolve_defaults` (URL params) and
   `resolve_bool_flags` (execution flags) serve different concerns. Keep them separate.

## References

- Commit `051ca28` — the "low effort" approach this ADR replaces.
- Refactoring plan: see conversation artifacts for step-by-step implementation.
- Related: `MissingType` / `MISSING` sentinel documented in [AGENTS.md](../../AGENTS.md) under "Sentinels & Missing Values."
