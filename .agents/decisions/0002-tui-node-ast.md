# ADR 0002: TUI Node AST Architecture

---
status: accepted
date: 2026-04-05
decider: Agent
---

## Context

The TUI's configuration rendering (`widgets.py`) and selection logic (`app.py`) rely heavily on nested `isinstance` checks to navigate raw `dict`/`list` structures. This breaks down as the TOML structure becomes more complex (dotted keys, custom tables, list-of-tables).

We need a way to shift "rendering complexity" into "data structure complexity" using the polymorphism principle from ADR 0001.

## Decision

We will implement a polymorphic **ConfigNode AST** for the TUI:

1.  **`ConfigNode` Protocol**: A baseline interface (`path()`, `key()`, `children()`, `doc_target()`).
2.  **Concrete Nodes**: `DictNode`, `ListNode`, `ScalarNode`, `LinterNode`, and `RulesCollectionNode`.
3.  **Recursive Wrapping**: A `wrap_data()` factory that converts raw TOML data into a `ConfigNode` tree during initial load.
4.  **UI-Layer Polymorphism**: Use `@singledispatchmethod` in widgets (e.g., `CategoryTable.render_node(node)`) to route rendering logic based on the node type, keeping Rich markup out of the model layer.

## Consequences

- **Pros**:
    - Centralized documentation routing (`doc_target()`).
    - Widgets no longer need to know "what" they are rendering, only "how" to render a `ConfigNode`.
    - Eliminates fragile nested type-inference logic.
- **Cons**:
    - Requires an additional "wrapping" step during data load.
    - Slightly more boilerplate in `src/ruff_sync/tui/types_.py`.

## References

- [ADR 0001: Type Refactoring Strategy](./0001-type-refactoring-strategy.md)
