# Implementation Plan: Phase 3 Type Refactoring (TUI Node AST)

This plan implements Phase 3 of the `type-checking` refactoring recommendations: replacing nested `isinstance` chains in TUI widgets with a structured internal AST/Node tree.

## User Review Required

> [!IMPORTANT]
> This refactor introduces a new `ConfigNode` protocol and several concrete implementations. This changes how data is stored and accessed within the TUI widgets' `data` attributes (moving from raw `dict`/`list` to `ConfigNode` objects).

- **Architectural Shift**: Complexity is "shifted" from the widget rendering logic (`widgets.py`) and selection handling (`app.py`) into polymorphic data models (`tui/models.py`).
- **State Management**: Nodes will now handle their own "summary" and "label" generation, as well as providing a unified interface for table row generation.

## Proposed Changes

### TUI Core Infrastructure

---

#### [NEW] [models.py](file:///Users/gabriel/dev/ruff-sync/src/ruff_sync/tui/models.py)

Create a dedicated models file for the TUI to define the node hierarchy.

- **`ConfigNode` (Protocol)**: Defines the interface for all TUI nodes.
    - `to_label()`: String for the tree node.
    - `to_summary()`: String for the inspector context.
    - `children()`: Returns child keys/nodes for tree expansion.
    - `table_data()`: Returns key/value pairs for the `CategoryTable`.
    - `is_expandable`: Property to determine if recursion should continue.
- **`DictNode`**, **`ListNode`**, **`ScalarNode`**: Standard TOML/JSON data wrappers.
- **`LinterNode`**, **`RulesCollectionNode`**: Specialized nodes for the rule status dashboard.
- **`wrap_data()`**: A factory function to recursively wrap raw data into nodes.

---

### TUI Widgets

---

#### [MODIFY] [widgets.py](file:///Users/gabriel/dev/ruff-sync/src/ruff_sync/tui/widgets.py)

- **`ConfigTree`**:
    - Update `populate()` to accept a `ConfigNode`.
    - Refactor `_populate_node()` to use `node.children()` instead of `if isinstance(data, dict): ...`.
- **`CategoryTable`**:
    - Refactor `update_content()` to accept a `ConfigNode` and use `node.table_data()`.
- **`RuleInspector`**:
    - Refactor `show_context()` to accept a `ConfigNode` and use `node.to_summary()`.

---

### TUI Application

---

#### [MODIFY] [app.py](file:///Users/gabriel/dev/ruff-sync/src/ruff_sync/tui/app.py)

- Update `on_mount()` to wrap the loaded `self.config` using `wrap_data()`.
- Refactor `handle_node_selected()`:
    - Instead of deep `if isinstance(data, dict) and data.get("type") == "linter"`, use `if isinstance(data, LinterNode)`.
    - Leverage polymorphic methods on the node if applicable, or keep type-checking shallow (against Classes, not raw types).

## Open Questions

- Should we include the `Arguments` object in the `ConfigNode` context for more advanced resolution, or keep it focused strictly on data representation?
    - *Initial Thought*: Keep it focused on data, passing necessary state (like `effective_rules`) during the wrap phase.

## Verification Plan

### Automated Tests
- Create `tests/test_tui_models.py` to verify `wrap_data` and node methods.
- Run `uv run mypy .` to ensure the new `ConfigNode` protocol is correctly implemented.

### Manual Verification
- Open the TUI (`uv run python -m ruff_sync inspect`).
- Verify that navigating the tree (drill-down into `lint.select`, `lint.extend-select`, etc.) works.
- Verify that clicking "Effective Rule Status" correctly populates the table and inspector.
- Verify that clicking a Linter Group (e.g., `Pyflakes`) correctly filters the table view.
- Verify that clicking an individual configuration value updates the inspector summary.
