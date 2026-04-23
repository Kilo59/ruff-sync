# Implementation Guide: Subdirectory Config Generation (Issue #176)

This document is designed to guide an AI agent through implementing "Option B: Subdirectory Config Generation". It breaks the feature down into isolated, sequential tasks, each assigned a complexity score so you can decide which agent model to deploy for which step.

## Feature Overview
When `ruff-sync` runs with `--to <subdirectory>/ruff.toml` (e.g., `tests/ruff.toml`), it must generate a **standalone, self-contained configuration** rather than relying on `extend = "../pyproject.toml"`. 

To do this successfully without breaking existing ignore rules, the agent must intercept the upstream configuration before merging, and rewrite the `per-file-ignores` glob patterns so they are relative to the new target directory. It must also strip out any `extend` keys to enforce isolation.

---

## Task Breakdown

### Task 1: Create the Path Rewriting Utility (Complexity: 4/5 - High)
*Requires careful handling of `tomlkit` proxy objects and string manipulation.*

**File to modify:** `src/ruff_sync/core.py`
**Goal:** Create a pure, isolated function to handle the logic of glob rewriting.
**Implementation details:**
1. Define a function: `def _rewrite_per_file_ignores(per_file_ignores: tomlkit.items.Table, rel_dir: str) -> tomlkit.items.Table:`
2. Create a fresh `tomlkit.table()` to hold the updated rules.
3. Iterate over the keys (glob patterns) and values (ignored rules) of the input table.
4. Implement the following routing logic for each key:
   - **Direct Match:** If the key starts with `rel_dir + "/"` (e.g., `"tests/**/*.py"` when `rel_dir="tests"`), strip the prefix so it becomes `"**/*.py"`, and add it to the new table with the same values.
   - **Global Match:** If the key does *not* contain a directory separator (e.g., `"*.py"`) or starts with `**/` (e.g., `"**/*.py"`), keep it exactly as-is and add it to the new table.
   - **Irrelevant Match:** If the key starts with a *different* directory prefix (e.g., `"scripts/**/*.py"` when `rel_dir="tests"`), **discard it**. Do not add it to the new table.
5. Return the newly constructed table.

### Task 2: Unit Test the Rewriting Utility (Complexity: 2/5 - Low)
*Great task for a basic coding agent.*

**File to modify:** `tests/test_toml_operations.py` (or create a new test file)
**Goal:** Validate the pure function from Task 1.
**Implementation details:**
1. Create a mock `tomlkit.table()` with the following keys:
   - `"tests/**/*.py" = ["T201"]`
   - `"**/*.py" = ["D100"]`
   - `"scripts/utils.py" = ["S101"]`
2. Pass it to `_rewrite_per_file_ignores` with `rel_dir="tests"`.
3. Assert that the resulting table contains:
   - `"**/*.py" = ["T201"]` (Prefix stripped)
   - `"**/*.py" = ["D100"]` (Global kept)
   - The `"scripts/utils.py"` key is completely absent.

### Task 3: Intercept and Rewrite During Sync (Complexity: 4/5 - High)
*Requires understanding the flow of the `sync_config` / `_merge_multiple_upstreams` pipeline.*

**File to modify:** `src/ruff_sync/core.py`
**Goal:** Apply the rewriting logic during the actual synchronization process.
**Implementation details:**
1. Inside the merge pipeline (likely in `_merge_multiple_upstreams` or wherever the upstream config is parsed), calculate `rel_dir`. 
   - If the user specified `--to tests/ruff.toml`, `rel_dir` should be `"tests"`. 
   - If `--to pyproject.toml`, `rel_dir` is `"."` or empty.
2. If `rel_dir` indicates a subdirectory:
   - Locate the `[tool.ruff.lint.per-file-ignores]` or `[lint.per-file-ignores]` table in the **parsed upstream config**.
   - Pass this table through `_rewrite_per_file_ignores`.
   - Replace the original table in the upstream config with the rewritten one.
3. Allow the existing `_recursive_update(target_config, upstream_config)` to proceed normally.

### Task 4: Enforce Standalone Configuration (Complexity: 1/5 - Very Low)
*Extremely simple dictionary manipulation.*

**File to modify:** `src/ruff_sync/core.py`
**Goal:** Ensure subdirectory configs don't leak settings from parents.
**Implementation details:**
1. After the merge is complete, check if we are targeting a subdirectory (`rel_dir != "."`).
2. If so, check if the key `"extend"` exists at the root level of the final `target_config`.
3. If it exists, delete it (`del target_config["extend"]`).

### Task 5: End-to-End Integration Test (Complexity: 3/5 - Medium)
*Requires knowledge of the project's fixture scaffolding workflow.*

**File to modify:** `tests/test_e2e.py` & `tests/lifecycle_tomls/`
**Goal:** Prove the CLI correctly handles subdirectory generation.
**Implementation details:**
1. Use the project's `invoke new-case` task to scaffold a new test case (e.g., `subdirectory_config`).
2. Set up the `upstream.toml` with a mix of global and subdirectory-specific `per-file-ignores`.
3. Set up the `initial.toml` as an empty file representing `tests/ruff.toml`.
4. Set up the `final.toml` with the expected rewritten ignores and no `extend` key.
5. Ensure the new case is covered by the E2E test runner.

---

## Agent Handoff Recommendations

- **Use a basic/faster model** for **Task 2**, **Task 4**, and **Task 5**. These require straightforward syntax implementation, basic assertions, and scaffolding based on existing patterns.
- **Use an advanced reasoning model** for **Task 1** and **Task 3**. Modifying `tomlkit` proxy tables safely without breaking formatting, and correctly hooking into the merge pipeline without causing regressions, requires deep contextual awareness.
