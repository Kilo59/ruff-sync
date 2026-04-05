---
name: type-checking
description: >-
  Systematic, procedural workflows for resolving complex Python 3.10 static type
  issues without typing.cast. Trigger on mypy errors, union ambiguity, or
  structural subtyping needs.
---

# Type-Checking Skill: Rigorous Resolution

This skill provides procedural workflows for resolving static type ambiguity in the `ruff-sync` project's strict environment. Use these procedures to satisfy Mypy without violating the project-wide ban on `typing.cast`.

## Procedure: Rigorous Type Resolution

Follow these steps for ANY Mypy error that isn't a simple typo:

1. **Reveal Inferred Type**:
   - Insert `reveal_type(expression)` before the failing line.
   - Run `uv run mypy` and note the output (e.g., `Revealed type is "Union[str, None]"`).
2. **Identify the Gap**:
   - Compare the "Revealed Type" with the "Expected Type" in the error message.
   - Determine if the issue is **Ambiguity** (Mypy is too broad) or **Incompatibility** (Types don't match).
3. **Select Narrowing Technique**:
   - Consult the [Narrowing Decision Tree](#narrowing-decision-tree) below.
4. **Apply and Verify**:
   - Implement the chosen narrowing (e.g., `isinstance`, `TypeIs`).
   - Remove `reveal_type` and run `uv run mypy` to confirm the fix.
5. **Check for Regressions**:
   - Use `reveal_type` on the same expression *after* narrowing to ensure it has reached the exact target type (not just a narrower union).

## Narrowing Decision Tree

Use this tree to choose the most robust narrowing technique for the project:

- **Is it a Union including `None`?**
  - **Yes**: Use `if x is not None:` or `assert x is not None`.
- **Is it a Union of two distinct types (e.g. `str | int`)?**
  - **Yes**: Use `typing_extensions.TypeIs` to partition the type. See [Advanced Narrowing](references/advanced-narrowing.md).
- **Is it a Union of related classes?**
  - **Yes**: Use `isinstance(x, TargetClass)`.
- **Is it a "capability" check (e.g., does it have `.read()`)?**
  - **Yes**: Define a `@runtime_checkable Protocol` and use `isinstance(x, MyProtocol)`. See [Protocol Patterns](references/protocol-patterns.md).
- **Is it a project-specific sentinel (`MISSING`)?**
  - **Yes**: Use `if x is not MISSING:`.

## Cast-less Refactoring Patterns

| Scenario | "Forbidden" Cast | "Rigorous" Alternative |
| :--- | :--- | :--- |
| **Indexing Dicts** | `cast(str, d["key"])` | `val = d["key"]; assert isinstance(val, str); return val` |
| **Union Returns** | `cast(A, get_union())` | `res = get_union(); if is_a(res): return res; raise TypeError(...)` |
| **Generic Variance** | `cast(List[Base], list_sub)` | Annotate the `TypeVar` with `covariant=True`. |

## Procedural Gotchas

- **Avoid Bare `TypeGuard`**: For partitioning unions, `TypeIs` is superior because it informs Mypy about the `else` branch.
- **Protocol Overhead**: Only use `@runtime_checkable` if you actually need `isinstance` at runtime. For purely static structural typing, a simple `Protocol` is faster.
- **The `# type: ignore` Baseline**: Only use `# type: ignore[error-code]` if:
  1. You have proven the code is correct via `reveal_type`.
  2. You have exhausted the Decision Tree.
  3. You have called out the reason to the user (e.g., "Mypy cannot handle this recursive Protocol").

## References

- [Mypy Error Lookup](references/error-code-lookup.md) — What to do for specific error codes.
- [Advanced Narrowing](references/advanced-narrowing.md) — Mastering `TypeIs`.
- [Protocol Patterns](references/protocol-patterns.md) — Structural typing workflows.
- [Generics Deep Dive](references/generics.md) — Covariance and Contravariance in 3.10.
