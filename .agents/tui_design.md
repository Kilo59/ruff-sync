# Implementation Plan: Ruff-Sync Read-Only TUI (`inspect`)

This document provides a thorough, step-by-step technical design for implementing the initial "Read-Only" TUI to interrogate and visualize `ruff` configurations. This follows the requirements established in `.agents/tui_requirements.md`.

---

## 1. Pre-Requisite Refactoring & Architecture Upgrades

Before we build the TUI feature itself, some of the existing codebase should be refactored to better support isolated Data Access and Subprocess management.

### A. Subprocess Wrapper (`src/ruff_sync/system.py` or `ruff_cli.py`)
Currently, `ruff-sync` is primarily concerned with TOML serialization. The TUI introduces a requirement to execute the system `ruff` binary (e.g. `ruff rule <CODE>`).
**Refactoring Task:**
- Create a generalized, safe abstraction for interacting with the `ruff` executable.
- Provide a typed function `async def get_ruff_rule_markdown(rule_code: str) -> str | None` that uses `asyncio.create_subprocess_exec` (or threads with `subprocess`) to fetch and return the rule text. This prevents raw `subprocess` sprawl across TUI widgets.

### B. Configuration Reader Extraction (`src/ruff_sync/config_io.py` or similar)
Right now, discovering and extracting the local `pyproject.toml` is slightly coupled to the lifecycle of pulling from upstreams (`pull()` / `check()` in `core.py`).
**Refactoring Task:**
- Extract a clean Data Access Object or helper (e.g., `def load_local_ruff_config(path: Path) -> dict[str, Any]`) that utilizes `resolve_target_path`, parses via `tomlkit`, and automatically calls `.unwrap()` to return a plain, read-only Python dictionary. This insulates the Textual app from navigating bizarre `tomlkit` proxy tables.

---

## 2. Dependency & CLI Integration

### [MODIFY] pyproject.toml
- Under `[project.optional-dependencies]`, define the `tui` extra explicitly pinning the Textual version framework (v8.x.x):
  ```toml
  [project.optional-dependencies]
  tui = ["textual>=0.81.0"]
  ```

### [MODIFY] src/ruff_sync/cli.py
- Add an `inspect` subcommand to `PARSER` inside `_get_cli_parser()`:
  ```python
  inspect_parser = subparsers.add_parser(
      "inspect",
      parents=[common_parser],
      help="Open a Terminal UI to explore and interrogate your local ruff configuration."
  )
  ```
- In `main()`, route the `inspect` command to a lazy-loaded wrapper:
  ```python
  if exec_args.command == "inspect":
      from ruff_sync.dependencies import require_dependency
      require_dependency("textual", "tui")

      from ruff_sync.tui.app import RuffSyncApp
      return RuffSyncApp(exec_args).run()
  ```

---

## 3. TUI Application Structure & Views

### [NEW] src/ruff_sync/tui/__init__.py
- Mark as a Python package.

### [NEW] src/ruff_sync/tui/app.py
- Define `RuffSyncApp` subclassing `textual.app.App`.
- **CSS**: Define embedded TCSS.
  - Layout: `Horizontal` split with `Tree` (left) sized `1fr`, and a `Vertical` container (right) sized `2fr`. Left side for Navigation, right side for Content & Inspector.
- **Compose Method**:
  ```python
  def compose(self) -> ComposeResult:
      yield Header()
      with Horizontal():
          yield ConfigTree(id="config-tree")
          with Vertical():
              yield CategoryTable(id="category-table")
              yield RuleInspector(id="inspector", classes="hidden")
      yield Footer()
  ```
- **Lifecycle (`on_mount`)**:
  - Automatically load `[tool.ruff]` via our refactored reader function.
  - Populate the `ConfigTree` with top-level keys (`lint`, `format`, etc.).

### [NEW] src/ruff_sync/tui/widgets.py
Contains all custom Textual widgets required for this view.

**1. `ConfigTree` (inherits `textual.widgets.Tree`)**:
- Parses the unwrapped dictionary representation of the Ruff config.
- Builds interactive nodes for structural hierarchies (e.g. `lint.select`, `format`).

**2. `CategoryTable` (inherits `textual.widgets.DataTable`)**:
- Displays key-value sets dynamically.
- Automatically clears and updates columns/rows when a tree node is highlighted.

**3. `RuleInspector` (inherits `textual.widgets.Markdown`)**:
- Displays `ruff rule <CODE>` output.
- Features an `async def fetch_and_display(self, rule_code: str)` method.
- **Background Worker**: Uses Textual `@work(thread=True)` to execute our refactored `get_ruff_rule_markdown()` function.

---

## 4. Textual Events & Data Flow

### [MODIFY] src/ruff_sync/tui/app.py (Reactivity)
- Tie widgets together using Textual's event routing (`@on`):
  - `@on(Tree.NodeSelected)`:
      - If the node is a configuration section (e.g. `lint.isort`), hide the Inspector and populate the `CategoryTable` with settings.
      - If the node represents a list of rules (unwrapped `lint.select`), display the active rule list in the table.
  - `@on(DataTable.RowSelected)`:
      - If the focused row represents a Ruff Rule Code (e.g., `RUF012`), reveal the `RuleInspector` widget and call `inspector.fetch_and_display("RUF012")`.
      - Expose related context natively based on selections.

---

## 5. Strict Static Typing & mypy Guidelines

Because `ruff-sync` operates under strict mypy regulations, the TUI module must explicitly conform to static type safety.

**Key Typing Considerations:**
1. **Textual App Generics:** Subclass `App` with its expected return type. If the app just runs and quits without returning a value, define it as `class RuffSyncApp(App[None]):`.
2. **Event Handler Signatures:** Utilize specific type hints internally provided by Textual for event payloads. For example:
   ```python
   async def on_tree_node_selected(self, event: Tree.NodeSelected[Any]) -> None:
   ```
3. **Handling `tomlkit` Types (NO `cast`):** `tomlkit`'s proxy objects often resolve ambiguously. Because `typing.cast` is forbidden in production code, when calling `.unwrap()` inside the `ConfigReader` refactor, you **must use explicit `isinstance` checks`** or `TypeGuard` functions (e.g. `if not isinstance(unwrapped_data, dict): raise TypeError(...)`) to strictly narrow the type initially.
4. **Structured Data over Dicts:** Instead of passing around plain `dict[str, Any]` between the Data Access Object and the Textual widgets, deeply recommend defining and using `TypedDict` or `NamedTuple` objects for predictable configuration structures. This provides significantly better type safety down the pipeline.
5. **Subprocess IO:** The new `ruff_cli.py` utility function `get_ruff_rule_markdown()` must explicitly declare its return values (`-> str | None`) and the subprocess decoding pipeline should clearly handle `bytes` versus `str` boundary conversions.

---

## 6. Verification Plan

### Automated Tests
- Scaffold `tests/test_tui.py`.
- Mock out `get_ruff_rule_markdown()` to reliably return stub Markdown documents.
- Use `textual.app.App.run_test()` to:
  1. Boot the application.
  2. Synthetically select a configuration section and assert the `DataTable` correctly hydrates.
  3. Select a documented rule row and assert the `RuleInspector` Markdown widget transitions from hidden to visible and displays the mock documentation.
  4. Ensure `ImportError` gracefully catches environments that attempt to run the feature without installing `ruff-sync[tui]`.

### Manual Testing Protocol
1. Install feature branch `pip install -e '.[tui]'`.
2. Execute `uv run ruff-sync inspect` locally.
3. Validate visual tree correctly reflects the active target `pyproject.toml`.
4. Highlight rules to ensure rendering triggers asynchronously without locking the UI process block.
