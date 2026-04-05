# Type-Checking Refactoring Recommendations

Based on the newly established `type-checking` skill and its emphasis on "Healthy Abstraction", "Complexity Shifting", and avoiding `isinstance` chains and unstructured `Any` types, the following refactorings are recommended for the `ruff-sync` project.

These implementations should be carried out to align the codebase with strategic typing practices.

---

## 1. Eliminate unstructured `dict[str, Any]` in TUI and System modules

**Target Files:**
- `src/ruff_sync/tui/app.py`
- `src/ruff_sync/tui/widgets.py`
- `src/ruff_sync/tui/screens.py`
- `src/ruff_sync/system.py`

**The Problem:**
The codebase frequently relies on `dict[str, Any]` and `list[dict[str, Any]]` to pass around Ruff rules, linters, and configuration contexts. The `type-checking` skill explicitly states: *"A well-named Generic is 10x clearer than a Mapping[str, Any]."* Relying on raw dictionaries forces developers to guess the keys at runtime.

**The Solution:**
Introduce `TypedDict` structures for the core payloads returned by the system and consumed by the TUI:
```python
from typing import TypedDict

class RuffRule(TypedDict):
    name: str
    code: str
    description: str
    # ... other relevant fields

class RuffLinter(TypedDict):
    prefix: str
    name: str
    # ...
```
Refactor `system.get_all_ruff_rules()` and `system.get_ruff_linters()` to return `list[RuffRule]` and `list[RuffLinter]` instead of `list[dict[str, Any]]`. Carry this typing up into `app.py`, `screens.py`, and `widgets.py`.

---

## 2. Refactor Recursive `isinstance` Chains in TUI Widgets

**Target Files:**
- `src/ruff_sync/tui/widgets.py` (Lines 93, 98, 163, 235)
- `src/ruff_sync/tui/app.py` (Line 188)

**The Problem:**
Extensive `if isinstance(data, dict): ... elif isinstance(data, list): ...` chains exist heavily within the TUI widgets when trying to parse or render nested configuration trees. This violates the `isinstance` chaining limit outlined in the type-checking guidance.

**The Solution:**
Apply the **Polymorphism** and **Complexity Shifting** principles:
- **Solution A:** Rather than passing raw nested dicts/lists to UI widgets and forcing the widget to perform data-type inference, normalize the incoming data into a structured generic format or `Node` protocol before rendering.
- **Solution B:** Use the `@singledispatch` or `@singledispatchmethod` decorator from `functools` to cleanly route data rendering without explicitly deep `if/elif` type checks.

---

## 3. Harden the Core TOML Merging Functions (`core.py`)

**Target File:**
- `src/ruff_sync/core.py`

**The Problem:**
The `_recursive_update` and other merge functions use `Any` heavily (e.g., `_recursive_update(source_table: Any, upstream: Any)` and setting `target: Any = tbl`). `tomlkit` proxy types can be tricky, but defaulting to `Any` weakens the structural typing of the project's most critical infrastructure.

**The Solution:**
Apply **Strategic Complexity (High-ROI typing)**. The core config merging logic is central to `ruff-sync`, making it an ideal candidate for "spending complexity in the infrastructure to buy simplicity in the features."
- Refactor the typing from `Any` to explicit `tomlkit` bounds (`tomlkit.items.Item`, `tomlkit.items.Table`, `tomlkit.container.Container`).
- If `tomlkit` types are too noisy, define a localized structural `@runtime_checkable Protocol` that maps out the getters and setters that `core.py` actually accesses.
- Remove `Any` when instantiating `source_val` and `merged_val`.

---

## 4. Resolve `isinstance` Union Branches in High-Level Logic

**Target Files:**
- `src/ruff_sync/cli.py` (Line 361)
- `src/ruff_sync/core.py` (Line 717)

**The Problem:**
The codebase sometimes uses `isinstance` to distinguish between success values vs error values, or strings vs paths/urls (e.g., `isinstance(res, BaseException)`).

**The Solution:**
- In `core.py`, shift towards a robust `Result` type or tuple pattern containing `(SuccessVal, None)` or `(None, ErrorVal)` rather than passing `res` as a Union and checking `isinstance(res, BaseException)`. Let the generics system protect against invalid access.
- In `cli.py`, unify the configuration upstream parsing upfront, reducing the variables to exactly one robust type before it starts routing logic.

---

## Summary of Next Steps

1. **Phase 1:** Add `TypedDict` declarations in a data-models file (or `types.py`/`system.py`) and replace all corresponding generic `dict[str, Any]` typings inside `system.py` and across the TUI application.
2. **Phase 2:** Refactor the TOML merging tree (`src/ruff_sync/core.py`) to eliminate `Any` parameters, replacing them with standard `tomlkit` generic objects (`Table`, `Array`).
3. **Phase 3:** Address the nested `isinstance` logic in `tui/widgets.py` by converting raw payloads into an internal AST / Node tree prior to rendering.
