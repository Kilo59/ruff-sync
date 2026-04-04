# Ruff-Sync TUI Requirements Document

## 1. Overview & Objectives

**Goal:** Create a Terminal User Interface (TUI) that allows developers to easily interrogate, understand, and eventually manipulate their `Ruff` configuration managed by `ruff-sync`.

**Problem Statement:** Configuration files (`pyproject.toml`) can grow large and difficult to navigate. Understanding why certain Ruff rules are active, where they came from (upstream vs. local overrides), and what exactly those rules do currently requires manual parsing and running independent CLI commands (`ruff rule <CODE>`).

**Vision:** Providing a rich, responsive Textual-based UI that acts as a "configuration dashboard." The initial release will focus strictly on a **Read-Only** interrogation interface. Future iterations will introduce read-write capabilities to interactively merge upstream changes during a `ruff-sync` pull.

---

## 2. Initial Implementation (Read-Only Interface)

### 2.1 Core Features
1. **Hierarchical Explorer view**
   - Provide a graphical tree or list view parsing the local `pyproject.toml` (`[tool.ruff]` section).
   - Easily drill down into sub-sections like `lint.select`, `lint.ignore`, `format`, and `lint.isort`.
2. **Active Rules Navigator**
   - Aggregate and display all currently active linting rules.
   - Provide visual grouping for rule categories (e.g., `E` for pycodestyle, `F` for Pyflakes, `TC` for flake8-type-checking).
3. **Rule Context & Documentation (Interrogation)**
   - When a user highlights/selects a specific rule (e.g., `RUF012`), display the official Ruff documentation.
   - Behind the scenes, the TUI should asynchronously execute `ruff rule <CODE>` to fetch the documentation and render it as Markdown in a side/inspector panel.
4. **Configuration Provenance (Drift Insight)**
   - Leverage `ruff-sync`'s core logic to identify if a setting matches the upstream `ruff-sync` source or if it is a local override.
   - Visually distinguish local modifications (e.g., using different Textual widget colors or icons).
5. **Fuzzy Search**
   - A search bar to quickly locate a specific configuration key or rule code without manual scrolling.

### 2.2 UX / UI Layout Concept
- **Header:** Application title and current local repository path.
- **Left Sidebar (Navigation):** `Tree` widget for configuration categories (`Global`, `Linting`, `Formatting`, `Rule Index`).
- **Center Area (Main Content):** `DataTable` or `ListView` showing the keys and values for the selected category.
- **Right/Bottom Panel (Inspector):** Context-aware documentation. Standard `Static` or `Markdown` widget to show rule explanations dynamically.
- **Footer:** Action key bindings (`q` to Quit, `/` to Search, `?` for Help).

---

## 3. Future Scope (Read-Write & Interactive Sync)

Once the read-only layer is stabilized, the UI will be expanded into an interactive configuration manager.

1. **Interactive `ruff-sync` Merge:**
   - Instead of blindly accepting the upstream TOML merge or just running `--check`, the TUI presents a side-by-side or inline diff mechanism.
   - Users can step through the proposed upstream changes and Accept/Reject them on a per-key basis.
2. **Local Modification Engine:**
   - Allow users to toggle rules on/off (add/remove from `lint.select` or `lint.ignore`) visually.
   - Persist changes to disk using `tomlkit` to guarantee that whitespace, comments, and file structure are preserved exactly as they were.

---

## 4. Technical Constraints & Architecture

- **UI Framework:** [Textual](https://textual.textualize.io/) (v8.x.x). Must follow its progressive standard (TCSS for styling, reactivity for state updates).
- **Asynchronous Execution:**
  - Any potentially blocking operations like fetching GitHub upstream configs or running `ruff rule` via `subprocess` MUST be wrapped in Textual background workers (`self.run_worker()`) to avoid blocking the main TUI thread.
- **Data Layer:**
  - Read operations should rely on the existing `tomlkit` and `core` parsing APIs within `ruff-sync`.
  - Type-safety must be maintained; the TUI components should interface cleanly with `ruff-sync`'s strictly typed dictionary/mapping representations.
- **Optional Dependency Integration:**
  - The TUI should be an optional CLI feature to keep the primary dependency size low. It should be bundled as `ruff-sync[tui]`, checking for `textual` availability before launching (following the optional dependency pattern).
