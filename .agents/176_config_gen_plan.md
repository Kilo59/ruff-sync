# Implementation Guide: Subdirectory Config Generation (Issue #176)

This document is designed to guide an AI agent through implementing "Option B: Standalone Subdirectory Config Generation". It breaks the feature down into isolated, sequential tasks, each assigned a complexity score so you can decide which agent model to deploy for which step.

## Feature Overview & DX (Opt-in)
Generating a standalone config involves "magic" (rewriting glob paths and stripping `extend`). To ensure a predictable Developer Experience (DX) and avoid surprising users, this feature must be strictly **opt-in**.

Users must explicitly pass a `--standalone` flag (or `standalone = true` in config) when syncing to a subdirectory to trigger the path-rewriting and isolation logic. Without this flag, `ruff-sync` should behave exactly as it does today (syncing the upstream configuration verbatim).

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

### Task 3: Unit Test the Rewriting Utility (Complexity: 2/5 - Low)
*Great task for a basic coding agent.*

**File to modify:** `tests/test_toml_operations.py` (or create a new test file)
**Goal:** Validate the pure function from Task 2.
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

## User Review Required

> [!IMPORTANT]
> The `--standalone` flag allows users to opt-in to this feature explicitly. Does this approach satisfy your requirements for maintaining a predictable DX?

Please review and approve this updated plan to finalize the handover documentation!
