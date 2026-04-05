# ADR 0001: Type Refactoring Strategy

---
status: accepted
date: 2026-04-05
decider: Agent
---

## Context

The `ruff-sync` codebase, particularly the TUI and TOML merging logic, has historically relied on `dict[str, Any]` and deep `isinstance` checks. This makes the codebase difficult to maintain, prone to runtime errors, and provides poor IDE support.

Based on the establishing `type-checking` skill, we need a strategic approach to "Complexity Shifting" and "Healthy Abstraction".

## Decision

We will implement a multi-phase type-refactoring strategy:

1.  **Eliminate unstructured `dict[str, Any]`**: Introduce `TypedDict` for core payloads (Ruff rules, linters) in the TUI and System modules.
2.  **Polymorphic TUI Widgets**: Replace recursive `isinstance(data, dict/list)` chains in widgets with structural polymorphism (e.g., `@singledispatchmethod` or a dedicated Node AST).
3.  **Strategic Complexity (High-ROI typing)**: Apply strict typing (`tomlkit` bounds) to core infrastructure like `core.py` (TOML merging) while keeping feature code simple.
4.  **Result Type Patterns**: Shift away from `Union[Success, Error]` with `isinstance` checks towards robust `Result` or tuple patterns.

## Consequences

- **Pros**:
    - Improved static analysis via `mypy`.
    - Better developer experience (autocompletion, go-to-definition).
    - Reduced runtime "surprises" in complex TOML merges.
- **Cons**:
    - Initial "complexity tax" in core infrastructure types.
    - Requires wrapping raw TOML data into structured nodes before rendering.

## References

- [type-checking skill](../skills/type-checking/SKILL.md)
