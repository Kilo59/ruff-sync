# Ruff-Sync TUI Requirements Document

## 1. Overview & Objectives

**Goal:** Create a Terminal User Interface (TUI) that allows developers to easily interrogate, understand, and eventually manipulate their `Ruff` configuration.

**Problem Statement:** Configuration files (`pyproject.toml`) can grow large and difficult to navigate. Understanding why certain Ruff rules are active and what exactly those rules do currently requires manual parsing and running independent CLI commands (`ruff rule <CODE>`).

**Vision:** Providing a rich, responsive Textual-based UI that acts as a local "configuration dashboard." The initial release will focus strictly on a **Read-Only** interrogation interface for the local `pyproject.toml`. Future iterations will introduce `ruff-sync` aware features to interactively review and merge upstream changes.

---

## 2. Initial Implementation (Read-Only Interface)

### 2.1 Core Features
1. **Hierarchical Explorer view**
   - Provide a graphical tree or list view parsing the local `pyproject.toml` (`[tool.ruff]` section).
   - Easily drill down into sub-sections like `lint.select`, `lint.ignore`, `format`, and `lint.isort`.
2. **Active Rules Navigator**
   - Aggregate and display all currently active linting rules.
   - Provide visual grouping for rule categories (e.g., `E` for pycodestyle, `F` for Pyflakes, `TC` for flake8-type-checking).
3. **Contextual Inspector & Documentation**
   - When a user highlights a specific rule (e.g., `RUF012`), asynchronously execute `ruff rule <CODE>` to fetch and render the official documentation as Markdown.
   - Surface related context depending on the selection: highlighting a rule exposes its documentation AND related configuration settings; highlighting a config setting might expose its structural definition or the specific rules it governs.
4. **Fuzzy Search**
   - A search bar to quickly locate a specific configuration key or rule code without manual scrolling.

### 2.2 UX / UI Layout Concept
- **Header:** Application title and current local repository path.
- **Left Sidebar (Navigation):** `Tree` widget for configuration categories (`Global`, `Linting`, `Formatting`, `Rule Index`).
- **Center Area (Main Content):** `DataTable` or `ListView` showing the keys and values for the selected category.
- **Right/Bottom Panel (Inspector):** Context-aware inspector. Because `ruff rule <CODE>` output contains proper Markdown, this panel MUST robustly render Markdown (e.g., utilizing Textual's `Markdown` widget) while dynamically adjoining related setting/rule cross-references around it.
- **Footer:** Action key bindings (`q` to Quit, `/` to Search, `?` for Help).

---

## 3. Future Scope (Read-Write & Interactive Sync)

Once the read-only layer is stabilized, the UI will be expanded into an interactive configuration manager and integrate with `ruff-sync` proper.

1. **Configuration Provenance (Drift Insight):**
   - Leverage `ruff-sync`'s core logic to identify if a setting natively matches the referenced upstream `ruff-sync` source or if it is a targeted local override.
   - Visually distinguish local modifications from upstream inherited configurations.
2. **Interactive `ruff-sync` Merge:**
   - Instead of blindly accepting the upstream TOML merge or just running `--check`, the TUI presents a side-by-side or inline diff mechanism.
   - Users can step through the proposed upstream changes and Accept/Reject them on a per-key basis.
3. **Local Modification Engine:**
   - Allow users to toggle rules on/off (add/remove from `lint.select` or `lint.ignore`) visually.
   - Persist changes to disk using `tomlkit` to guarantee that whitespace, comments, and file structure are preserved exactly as they were.
4. **Contextual Comment Attachment (TOML Parsing):**
   - Extract in-line and block comments from `pyproject.toml` using `tomlkit` to serve as extended contextual annotations within the UI.
   - Establish strict heuristic rules for comment association: e.g., comments immediately preceding a key belong to that key; inline trailing comments belong to that line's value; comments directly beneath a section header act as section descriptions.

---

## 4. Technical Constraints & Architecture

- **UI Framework:** [Textual](https://textual.textualize.io/) (v8.x.x). Must follow its progressive standard (TCSS for styling, reactivity for state updates). See our [Textual Skill](skills/textual/SKILL.md) for project-specific TUI implementation rules.
- **Asynchronous Execution:**
  - Any potentially blocking operations like fetching GitHub upstream configs or running `ruff rule` via `subprocess` MUST be wrapped in Textual background workers (`self.run_worker()`) to avoid blocking the main TUI thread.
- **Data Layer:**
  - Read operations should rely on the existing `tomlkit` and `core` parsing APIs within `ruff-sync`.
  - Type-safety must be maintained; the TUI components should interface cleanly with `ruff-sync`'s strictly typed dictionary/mapping representations.
- **Optional Dependency Integration:**
  - The TUI should be an optional CLI feature to keep the primary dependency size low. It should be bundled as `ruff-sync[tui]`, checking for `textual` availability before launching. Reference [DEPENDENCIES.md](DEPENDENCIES.md) for guidelines on our optional dependency and lazy-loading patterns.
