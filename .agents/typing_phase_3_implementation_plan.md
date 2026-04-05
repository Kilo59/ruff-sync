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

Create a dedicated models layer for the TUI to enforce structured payloads.

- **`ConfigNode` (Protocol)**: Defines the base interface for TUI nodes. Rather than bloating the model with UI-specific rendering strings, keep it focused on state:
    - `path()` / `key()`: Returns the node's configuration path or label.
    - `children()`: Returns child nodes for tree expansion.
    - `doc_target()`: Returns a `(target: str, doc_type: Literal["rule", "config", "none"])` tuple, eliminating path-building and regex guessing in `app.py`.
- **Concrete Nodes**: `DictNode`, `ListNode`, `ScalarNode`, `LinterNode`, `RulesCollectionNode`.
- **`wrap_data()`**: A factory function to recursively (or lazily) wrap the loaded configuration dictionary into instances of `ConfigNode`.

---

### TUI Widgets (Data Rendering via Singledispatch)

---

#### [MODIFY] [widgets.py](file:///Users/gabriel/dev/ruff-sync/src/ruff_sync/tui/widgets.py)

Instead of the model deciding *how* it looks (`node.table_data()`), shift rendering logic to the widgets using structural polymorphism.

- **Use `@singledispatchmethod`**:
    - In `CategoryTable`, replace `update_content()` and `update_rules()` with a single `@singledispatchmethod def render_node(self, node: ConfigNode)`.
    - Register specific rules for `render_node.register(LinterNode)`, `render_node.register(DictNode)`, etc. This keeps UI styling (like rich color markup `[success]`) strictly inside the UI layer, preventing the model layer from becoming entangled with Rich text formatting.
- **`ConfigTree`**:
    - Update `populate()` to accept a root `ConfigNode`.
    - `_populate_node()` becomes deeply flattened or leans on `node.children()`.
- **`RuleInspector`**:
    - `show_context()` delegates to `node.doc_target()` rather than trying to infer table length or list item counts manually.

---

### TUI Application (Event Routing)

---

#### [MODIFY] [app.py](file:///Users/gabriel/dev/ruff-sync/src/ruff_sync/tui/app.py)

- **Initialization**: Wrap the loaded config using `wrap_data()` in `on_mount()`.
- **Refactor `handle_node_selected()` and `handle_row_selected()`**:
    - Eliminate the deep `if data == "__rules__": ... elif data.get("type") == "linter": ...` logic.
    - Rely on `@singledispatchmethod` on the application handlers, or let the widgets process the strongly typed `ConfigNode` directly. The app can fetch documentation simply by querying `node.doc_target()`.

## Open Questions

- Should we include the `Arguments` object in the `ConfigNode` context for more advanced resolution, or keep it focused strictly on data representation?
    - *Proposed Direction*: Keep it strictly focused on data. State like `effective_rules` and `linters` can be passed into the `wrap_data()` factory and enclosed within the specific nodes that need them.
- How do we handle laziness? Eagerly walking the entire TOML tree to create Node instances during `on_mount` is fine for typical sizes, but might we want `DictNode.children()` to evaluate laziness to save memory?

## Verification Plan

### Automated Tests
- Create `tests/test_tui_models.py` to verify `wrap_data` handles deeply nested dicts/lists.
- Create explicit test verifying `@singledispatchmethod` correct invocation based on Node types.
- Ensure `uv run mypy .` is clean.

### Manual Verification
- Open the TUI (`uv run python -m ruff_sync inspect`).
- Verify that drill-down in the configuration tree still operates smoothly.
- Verify node selection fetches correct markdown documentation (validating `doc_target()`).
- Verify Linter group node selection updates the table correctly.
