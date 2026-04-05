---
name: type-checking
description: >-
  Systematic workflows for designing types, architecting classes, and resolving
  static type issues in Python 3.10. Trigger on "new class," "designing,"
  "refactoring," or "mypy errors." Prioritizes healthy design (Generics,
  Protocols) over narrowing.
---

# Type-Checking Skill: Balanced Resolution

This skill provides procedural workflows for resolving static type ambiguity in the `ruff-sync` project. It prioritizes **Healthy Abstraction** (Generics, Protocols) over both `typing.cast` and excessive `isinstance` checks.

## The Dominant Rule: Seek the Generics Sweet Spot

**A well-named Generic is 10x clearer than a Mapping[str, Any].**
- **Level 1/2 (Healthy)**: Use simple TypeVars for containers and interfaces. They are your first choice for polymorphism.
- **Level 3 (Strategic vs. Toxic)**: High complexity is ONLY justified if the **Value Added outweighs the cognitive burden.** See the [Generics Spectrum](references/refactoring-patterns.md).

## Heuristic: Complexity Shifting (The ROI Rule)

**"Spend complexity in the infrastructure to buy simplicity in the features."**
- **High-ROI (Strategic)**: A complex type signature is justified if it:
  1. Prevents `isinstance`, `Any`, or narrowing at 5+ downstream call sites.
  2. Protects a critical boundary (e.g., core merge engine, security logic).
  3. Provides a perfectly typed API for external/library-level consumption.
- **Low-ROI (Toxic)**: Avoid advanced types for one-off CLI logic, TUI layout internals, or test-specific utilities.

## Design-Phase Workflow (New Features)

When starting a new class, module, or interface:

1. **Sketch with Protocols**: Instead of a concrete base class, define the **behavior** you need as a `Protocol`.
2. **Apply Generics Early**: If your class handles "data" or "items," use a `Generic[T]` from the start to avoid later TypeVar refactors.
3. **Minimize Unions**: Design your data flow to avoid "Either A or B" as return types. Prefer Polymorphism (different classes for different states).
4. **The 10-Second Check**: If your new architectural diagram requires explaining the type variance for 5 minutes, simplify it.

## Procedure: Refactor or Narrow?

Follow this checklist *before* applying any narrowing technique:

1. **Check for Level 1/2 Generics**: Can a simple `TypeVar` make this more readable? (Yes -> **Do it!**)
2. **Evaluate Complexity Shifting (ROI)**: Does this reform remove the need for narrowing downstream?
   - **Yes**: Invest in the complexity (Strategic Level 3).
   - **No**: Stick to the 10-Second Rule.
3. **The 10-Second Rule**: If a signature cannot be understood in 10 seconds, it's too complex—unless it satisfies the **High-ROI** criteria above.
4. **Evaluate Boundary Status**: Is this an external boundary (e.g., loading config from TOML)?
   - **Yes**: Runtime narrowing (`isinstance`, `TypeIs`) is acceptable for validation.

## Narrowing Decision Tree (Last Resort)

1. **Is it a Union including `None`?** -> `if x is not None:`.
2. **Is it a partitioned Union (e.g. `str | int`)?** -> `TypeIs` for exhaustive branch narrowing.
3. **Is it a project-specific sentinel?** -> `if x is not MISSING:`.
4. **Is it a capability check?** -> `@runtime_checkable Protocol` (only if runtime check is required).

## References

- [Generics Spectrum](references/refactoring-patterns.md) — Strategic vs. Toxic examples.
- [Generics Best Practices](references/generics.md) — How to use TypeVars correctly in 3.10.
- [Error Code Lookup](references/error-code-lookup.md) — Mapping Mypy codes to project-safe fixes.
- [Protocol Patterns](references/protocol-patterns.md) — Structural typing workflows.
