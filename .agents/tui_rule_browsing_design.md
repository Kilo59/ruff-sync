# Detailed Implementation Plan: Effective Rules & Omnibox

This document provides exhaustive technical instructions to implement Features 1 (Effective Rules Flat Table) and 3 (Global Fuzzy Command Palette) from the [Rule Browsing Proposals](tui_rule_browsing.md).

---

## 1. Data Access & Subprocess Upgrades
To present a flat list of rules or allow fuzzy searching across all rules, the TUI must have structural knowledge of every rule Ruff supports.

### A. `get_all_ruff_rules() -> list[dict]`
- In `src/ruff_sync/system.py` (or the equivalent subprocess wrapper module), implement an async function that executes `uv run ruff rule --all --output-format json` (or `ruff rule --all --output-format json` depending on the environment context).
- This returns a JSON array of objects representing all rules (fields include `name`, `code`, `linter`, `summary`, etc.).

### B. `get_ruff_linters() -> list[dict]`
- Implement an async function that executes `ruff linter --output-format json`. Returns categories/prefixes (fields include `prefix`, `name`, `categories`).

### C. Active Rule Evaluation Logic
- Create a pure utility function `compute_effective_rules(all_rules: list[dict], toml_config: dict) -> list[dict]`.
- `toml_config` is the unwrapped TOML dictionary.
- The function iterates over `all_rules`. For each rule, it checks the rule's `code` (e.g. `F401`) against the `[tool.ruff.lint]` keys `select`, `ignore`, `extend-select`.
- **Heuristic**: Length-based prefix matching. If `select = ["F"]` and `ignore = ["F401"]`, `F401` matches both. Since `F401` (len 4) is a longer and more specific prefix match than `F` (len 1), `ignore` wins. The rule is marked with `status="Ignored"`. If it was only partially matched in `select` it gets `status="Enabled"`.
- Return an enriched list of dictionaries mimicking the original rules but adding a `status` key.

---

## 2. The "Effective Rules" Flat Table UI

### A. Tree Hierarchy Updates (`src/ruff_sync/tui/widgets.py`)
- Modify the `ConfigTree` (which parses the `pyproject.toml` hierarchy) to inject a synthetic root node at the very top: **"Effective Active Rules"**.

### B. Table Integration (`src/ruff_sync/tui/app.py` & `widgets.py`)
- When the user selects the "Effective Active Rules" tree node, intercept the event in `@on(Tree.NodeSelected)`.
- Make the `CategoryTable` visible and hide the `RuleInspector` initially.
- Clear existing columns and add `["Code", "Name", "Linter", "Status"]`.
- Fetch the enriched rules list from `compute_effective_rules`.
- Iterate the enriched rules, adding them to the `CategoryTable`. Use Textual Rich markup (e.g., `[green]Enabled[/green]`, `[red]Ignored[/red]`) for the Status column.

### C. Row Selection Linkage
- Ensure `@on(DataTable.RowSelected)` correctly parses the Row Data to extract the "Rule Code" (e.g. `F401`).
- Hiding the Table and revealing the `RuleInspector` should fire seamlessly by calling `self.query_one("#inspector").fetch_and_display(rule_code, is_rule=True)`.

---

## 3. The Global Fuzzy "Omnibox" UI

### A. App-Level Keybind (`src/ruff_sync/tui/app.py`)
- In `RuffSyncApp.BINDINGS`, add `("/", "search", "Search Rules")`.
- Add `def action_search(self) -> None:` to intercept the hotkey.

### B. `OmniboxScreen` Widget (`src/ruff_sync/tui/screens.py`)
- Create a module `screens.py` and define `class OmniboxScreen(ModalScreen[str]):`.
- `compose()` should yield an `Input(placeholder="Search rules (e.g. F401, unused)...")` and optionally an initially-empty `OptionList` or `ListView` beneath it for results.
- **TCSS**: Center the `OmniboxScreen` contents vertically and horizontally. Give the main container a distinct background color and border to pop out over the main App.

### C. Fuzzy Search Logic (`@on(Input.Changed)`)
- Read `all_rules` from the background fetching mechanism.
- For every keystroke (`Input.Changed`), perform a simple substring or fuzzy match against both `rule["code"]` and `rule["name"]`.
- Populate the `ListView`/`OptionList` with the top 10-15 matches.

### D. Submission (`@on(Input.Submitted)` or `OptionList.OptionSelected`)
- When the user hits enter on a search result, call `self.dismiss(result_rule_code)`.

### E. App Callback Integration
- In `action_search`, execute `self.push_screen(OmniboxScreen(), self.handle_omnibox_result)`.
- `def handle_omnibox_result(self, rule_code: str | None) -> None:`
- If `rule_code` is provided, act exactly as if a row was selected in the `CategoryTable`: Hide the table, show the inspector via `self.query_one("#inspector").fetch_and_display(rule_code, is_rule=True)`.
