# Ruff-Sync TUI: Rule Browsing & Discovery Proposals

This document outlines additional convenience features and alternative navigation paradigms for browsing and exploring specific Ruff rules and groups outside the standard TOML hierarchy.

**Related Documents:**
- [TUI Requirements](tui_requirements.md)
- [TUI Technical Design](tui_design.md)
- [Rule Browsing Detailed Design](tui_rule_browsing_design.md)

## Background
While the TOML hierarchy (as established in the core requirements) provides an exact structural representation (e.g., exposing `tool.ruff.lint.select`), it is not always the most intuitive way to discover or understand the net set of rules actively evaluating the project.

The following proposals are designed to augment the current "Read-Only" TUI mode to support rapid interrogation, global searching, and global discovery of Ruff rules.

---

## 1. The "Effective Rules" Flat Table
Instead of exclusively browsing via the TOML tree (`tool.ruff.lint.select`), we introduce a top-level **"Effective Rules"** dashboard.
- **How it works:** A single, sortable `DataTable` that flattens all configuration vectors (`select`, `extend-select`, `ignore`, `per-file-ignores`) into a definitive list.
- **Columns:** `Code` (e.g., F401), `Name` (e.g., unused-import), `Category` (e.g., Pyflakes), and `Status` (Enabled/Ignored).
- **Benefit:** Gives the user a complete, "at-a-glance" ledger of exactly what the linter is checking without having to manually perform the mental math of `select` minus `ignore`.

## 2. Category / Linter Prefix Grouping
Ruff is conceptually built around "Linters" (e.g., `Pyflakes`, `pycodestyle`, `flake8-bugbear`). The TOML configuration often just specifies a prefix like `select = ["E", "F", "B"]`.
- **How it works:** Add a new root node in the `Tree` called **"Linters & Categories"**.
- **Interaction:** Navigating to "flake8-bugbear (B)" displays a table of all `B` rules, instantly showing which ones are locally enabled, ignored, or inactive.
- **Benefit:** Maps directly to how developers usually think about adding new rulesets to their projects.

## 3. Global Fuzzy Command Palette ("Omnibox")
Navigating a tree or a table can be tedious if the user knows exactly what they are looking for.
- **How it works:** A global keybind (e.g., `Ctrl+P` or `/`) that opens a fuzzy search overlay modal.
- **Interaction:** The user types "unused" and the palette immediately surfaces `F401 (unused-import)`, `F841 (unused-variable)`, etc. Hitting Enter drops them directly into the `RuleInspector` for that specific rule, completely bypassing the Tree hierarchy.
- **Benefit:** The fastest possible way to interrogate a specific rule.

## 4. Quick-Filter State Toggles
When inside any view displaying rules (like the flattened table or the prefix grouping), give the user hotkeys to rapidly shift perspectives.
- **How it works:** Add toggles (e.g., `1: All`, `2: Enabled`, `3: Ignored`).
- **Benefit:** If a user is looking at a massive category like `E` (pycodestyle), they can quickly press `3` to filter the table down to ONLY the rules they explicitly ignored, providing an instant audit trail.

## 5. "Rule Registry" / Discovery Mode
Currently, the user only sees rules they explicitly mention in their `pyproject.toml` or have inherited. How do they discover new rules to adopt?
- **How it works:** By executing `ruff rule --all` under the hood, the TUI could populate a "Discovery" tab. This lists every single rule Ruff supports.
- **Visuals:** Rules that are currently enabled in the local project are highlighted or checked off.
- **Benefit:** Huge value-add for configuration exploration. Users can browse new rules they might want to adopt directly inside the TUI without referring back to the Ruff website.
