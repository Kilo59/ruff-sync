# Implementation Guide: Standalone Subdirectory Generation (Issue #176)

This document guides an AI agent through implementing the Standalone Subdirectory Config Generation feature in `ruff-sync`. It outlines the core user story, the technical problem, and breaks the implementation down into isolated, sequential tasks with complexity scores.

---

## The User Story

**As a maintainer of a multi-package repository or an organization standardizing linting,**
**I want** to use `ruff-sync` to automatically generate self-contained, standalone `ruff.toml` configurations for specific subdirectories (like `tests/` or `backend/`) from a single central upstream config,
**So that** I can isolate configurations, override global ignores, and provide developers with a single explicit source of truth that works flawlessly in their IDEs, without wrestling with complex `extend` inheritance chains.

### The Solution: The `--standalone` Flag
We are introducing the `--standalone` flag. When a user runs `ruff-sync --to tests/ruff.toml --standalone`, the tool acts as a **configuration compiler**. It takes the upstream config and "projects" it for the target subdirectory by filtering out irrelevant rules, rewriting glob paths so they remain valid, and stripping `extend` inheritance.

**Crucially, this is a fully self-contained duplication, not just an overrides file.** `ruff-sync`'s primary job is to sync the *entire* `[tool.ruff]` configuration (`select`, `ignore`, `line-length`, plugins, etc.) from the upstream source. When it generates `tests/ruff.toml`, it writes all of those global settings directly into the file. Because the new file physically contains the full rule selection, it does not *need* to inherit from `pyproject.toml` at runtime. Stripping `extend` is completely safe and desirable because the generated config is already a complete, hermetic replica.

**The Upstream Config (`https://.../pyproject.toml`):**
```toml
[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["T201", "S101"]
"scripts/**/*.py" = ["T201"]
"**/*.py" = ["D100"]
```

**The Generated Standalone Config (`tests/ruff.toml`):**
```toml
[lint.per-file-ignores]
"**/*.py" = ["T201", "S101"]  # Note: The "tests/" prefix was intelligently stripped
"**/*.py" = ["D100"]          # Global rules are kept as-is

# Note: The "scripts/**/*.py" rules were completely discarded because they don't apply here.
# Note: No `extend = "../pyproject.toml"` exists here. It is fully self-contained.
```

By rewriting `"tests/**/*.py"` into `"**/*.py"`, the rules maintain their exact semantic meaning within the context of the `tests/` directory, preventing the `"tests/tests/**/*.py"` path resolution bug from ever occurring.

---

## Task Breakdown

### Task 1: Add `--standalone` Config and CLI Flag (Complexity: 2/5 - Low)
*Basic CLI and type definitions update.*

**Files to modify:** `src/ruff_sync/cli.py`, `src/ruff_sync/constants.py`, `src/ruff_sync/core.py`
**Goal:** Expose the `standalone` option to the user.
**Implementation details:**
1. Update `Config` TypedDict in `core.py` to include `standalone: bool`.
2. Update `ExecutionArgs` and `Arguments` classes in `cli.py` to include `standalone: bool`.
3. Add a `--standalone` boolean flag to the argparse configuration in `cli.py`.
4. Ensure the flag value is correctly parsed and merged into the `ExecutionArgs` passed down to the core logic.

### Task 2: Create the Path Rewriting Utility (Complexity: 4/5 - High)
*Requires careful handling of `tomlkit` proxy objects and string manipulation.*

**File to modify:** `src/ruff_sync/core.py`
**Goal:** Create a pure, isolated function to handle the logic of glob rewriting shown in the "Before & After" example.
**Implementation details:**
1. Define a function: `def _rewrite_per_file_ignores(per_file_ignores: tomlkit.items.Table, rel_dir: str) -> tomlkit.items.Table:`
2. Create a fresh `tomlkit.table()` to hold the updated rules.
3. Iterate over the keys (glob patterns) and values (ignored rules) of the input table.
4. Implement the following routing logic for each key:
   - **Direct Match:** If the key starts with `rel_dir + "/"` (e.g., `"tests/**/*.py"` when `rel_dir="tests"`), strip the prefix so it becomes `"**/*.py"`, and add it to the new table with the same values.
   - **Global Match:** If the key does *not* contain a directory separator (e.g., `"*.py"`) or starts with `**/` (e.g., `"**/*.py"`), keep it exactly as-is and add it to the new table.
   - **Irrelevant Match:** If the key starts with a *different* directory prefix (e.g., `"scripts/**/*.py"` when `rel_dir="tests"`), **discard it**. Do not add it to the new table.
5. Return the newly constructed table.

### Task 3: Unit Test the Rewriting Utility (Complexity: 2/5 - Low)
*Great task for a basic coding agent.*

**File to modify:** `tests/test_toml_operations.py` (or create a new test file)
**Goal:** Validate the pure function from Task 2.
**Implementation details:**
1. Create a mock `tomlkit.table()` mimicking the "Before" example above.
2. Pass it to `_rewrite_per_file_ignores` with `rel_dir="tests"`.
3. Assert that the resulting table matches the "After" example exactly.

### Task 4: Intercept and Rewrite During Sync (Complexity: 4/5 - High)
*Requires understanding the flow of the `sync_config` / `_merge_multiple_upstreams` pipeline.*

**File to modify:** `src/ruff_sync/core.py`
**Goal:** Apply the rewriting logic during synchronization ONLY if `--standalone` is True.
**Implementation details:**
1. Inside the merge pipeline (`_merge_multiple_upstreams`), check if `args.standalone` is True.
2. If True, calculate `rel_dir` based on the `--to` flag's directory relative to the project root. (e.g., if targeting `tests/ruff.toml`, `rel_dir` is `"tests"`).
3. If `rel_dir` indicates a subdirectory:
   - Locate the `[tool.ruff.lint.per-file-ignores]` or `[lint.per-file-ignores]` table in the **parsed upstream config**.
   - Pass this table through `_rewrite_per_file_ignores`.
   - Replace the original table in the upstream config with the rewritten one.
4. Allow the existing `_recursive_update(target_config, upstream_config)` to proceed normally.

### Task 5: Enforce Standalone Configuration (Complexity: 1/5 - Very Low)
*Extremely simple dictionary manipulation.*

**File to modify:** `src/ruff_sync/core.py`
**Goal:** Ensure standalone configs don't leak settings from parents.
**Implementation details:**
1. After the merge is complete, check if `args.standalone` is True and `rel_dir != "."`.
2. Check if the key `"extend"` exists at the root level of the final `target_config`.
3. If it exists, delete it (`del target_config["extend"]`).

### Task 6: End-to-End Integration Test (Complexity: 3/5 - Medium)
*Requires knowledge of the project's fixture scaffolding workflow.*

**File to modify:** `tests/test_e2e.py` & `tests/lifecycle_tomls/`
**Goal:** Prove the CLI correctly handles `--standalone` generation.
**Implementation details:**
1. Use the project's `invoke new-case` task to scaffold a new test case (e.g., `subdirectory_standalone`).
2. Set up the `upstream.toml` with a mix of global and subdirectory-specific `per-file-ignores`.
3. Set up the `initial.toml` as an empty file representing `tests/ruff.toml`.
4. Ensure the test runner invokes `ruff-sync` with `--standalone` for this case.
5. Set up the `final.toml` with the expected rewritten ignores and no `extend` key.

---

## Agent Handoff Recommendations

- **Use a basic/faster model** for **Task 1**, **Task 3**, **Task 5**, and **Task 6**. These require straightforward syntax implementation, basic assertions, and scaffolding based on existing patterns.
- **Use an advanced reasoning model** for **Task 2** and **Task 4**. Modifying `tomlkit` proxy tables safely without breaking formatting, and correctly hooking into the recursive merge pipeline without causing regressions, requires deep contextual awareness.
