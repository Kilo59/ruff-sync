# Implementation Guide: Standalone Subdirectory Generation (Issue #176)

This document guides an AI agent through implementing the Standalone Subdirectory Config Generation feature in `ruff-sync`. It outlines the core user story, the iterative workflow, and breaks the implementation down into isolated, sequential tasks with complexity scores.

---

## The User Story & Iterative Workflow

**As a maintainer of a multi-package repository or an organization standardizing linting,**
**I want** to use `ruff-sync` to automatically generate self-contained, standalone `ruff.toml` configurations for specific subdirectories (like `tests/` or `apps/api/`) from my root configuration,
**So that** I can isolate configurations, override global ignores locally, and provide developers with a single explicit source of truth that works flawlessly in their IDEs, without wrestling with complex `extend` inheritance chains.

### The DX Gap: Analyzing User Workflows
To understand why manual CLI flags fail, consider these two common workflows:

**Story 1: The "I Just Want To Isolate Tests" Workflow**
1. **Initial Setup:** User runs `ruff-sync pull https://...` to sync their root `pyproject.toml` with company standards.
2. **The Problem:** The user realizes their `tests/` directory ignores aren't working in their IDE due to Ruff's glob path resolution bugs with `extend`.
3. **The Manual Fix:** They run `ruff-sync pull pyproject.toml --to tests/ruff.toml --standalone` to create a working, isolated config.
4. **Iteration Gap:** The user decides they want to ignore `S101` in tests, so they manually edit their root `pyproject.toml` to add `"tests/**/*.py" = ["T201", "S101"]`. *But nothing happens to `tests/ruff.toml`.* The user must *remember* to manually re-run the standalone generation command. If they forget, the root config and test config diverge silently.
5. **Remote Update Gap:** A week later, the company releases a new linting rule. The user runs `ruff-sync pull` to get the update. Again, `tests/ruff.toml` is now completely out of sync. The user has to run *two* separate `ruff-sync` commands every time they update their project.

**Story 2: The Monorepo Workspace**
1. **Goal:** A user has a monorepo with `packages/core`, `packages/utils`, and `apps/api`. They want a single source of truth at the root, but standalone configs for every package.
2. **Generation:** They manually run the standalone command 3 separate times for each sub-directory.
3. **Iteration Gap:** The user tweaks a global rule in the root `pyproject.toml`. They must now manually execute all three CLI commands again. In practice, they are forced to write a custom `sync.sh` bash script. If a user has to write a script to wrap a syncing tool, the syncing tool's DX has failed.

### The Solution: Declarative Two-Phase Cascade
Instead of manual CLI flags, we use a declarative `standalone-targets` array in `[tool.ruff-sync]` to completely eliminate the orchestration burden.

**The Root Config (`pyproject.toml`):**
```toml
[tool.ruff-sync]
upstream = "https://github.com/org/standards/pyproject.toml"
standalone-targets = [
    "tests/ruff.toml",
    "apps/api/ruff.toml"
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["T201", "S101"]
"**/*.py" = ["D100"]
```

When a user runs `ruff-sync pull`, the tool performs a **Two-Phase Cascade**:
1. **Phase 1 (Remote Sync):** Fetches `upstream` and merges it into the local `pyproject.toml`.
2. **Phase 2 (Local Projection):** Detects `standalone-targets`, reads the *newly updated* local `pyproject.toml`, and projects it into `tests/ruff.toml` by filtering out irrelevant rules, rewriting glob paths so they remain valid, and stripping `extend` inheritance.

**Crucially, the generated target is a fully self-contained duplication, not just an overrides file.** It physically contains the full rule selection, meaning it does not *need* to inherit from `pyproject.toml` at runtime.

---

## Task Breakdown

### Task 0: Support Local File Upstreams (Complexity: 2/5 - Low)
*Prerequisite for Phase 2 Projection.*
**File to modify:** `src/ruff_sync/core.py`
**Goal:** Allow `ruff-sync` to fetch from a local `pyproject.toml` instead of requiring a network URL.
**Implementation details:**
1. In `fetch_upstream_config`, check if `url.scheme` is empty or `"file"`.
2. If it is a local path, read the file directly using `pathlib.Path(url.path).read_text()` and return it as a `FetchResult` with a `StringIO` buffer.

### Task 1: Add `standalone_targets` Configuration (Complexity: 2/5 - Low)
**Files to modify:** `src/ruff_sync/core.py`, `src/ruff_sync/constants.py`, `src/ruff_sync/cli.py`
**Goal:** Parse the declarative array from pyproject.toml.
**Implementation details:**
1. Update `Config` TypedDict in `core.py` to include `standalone_targets: list[str]`.
2. Add `STANDALONE_TARGETS` to `ConfKey` in `constants.py`.
3. In `cli.py` (`get_config`), parse the array.

### Task 2: Create the Path Rewriting Utility (Complexity: 4/5 - High)
**File to modify:** `src/ruff_sync/core.py`
**Goal:** Create a pure, isolated function to handle the logic of glob rewriting.
**Implementation details:**
1. Define a function: `def _rewrite_per_file_ignores(per_file_ignores: tomlkit.items.Table, rel_dir: str) -> tomlkit.items.Table:`
2. Create a fresh `tomlkit.table()`.
3. Iterate over the keys (glob patterns).
4. **Direct Match:** If key starts with `rel_dir + "/"`, strip the prefix so `"tests/**/*.py"` becomes `"**/*.py"`.
5. **Global Match:** If key has no directory separator or starts with `**/`, keep it as-is.
6. **Irrelevant Match:** Otherwise, discard it.
7. Return the new table.

### Task 3: Unit Test the Rewriting Utility (Complexity: 2/5 - Low)
**File to modify:** `tests/test_toml_operations.py`
**Goal:** Validate Task 2.

### Task 4: Implement Phase 2 Cascading Sync (Complexity: 5/5 - High)
**File to modify:** `src/ruff_sync/core.py`
**Goal:** Execute the two-phase cascade.
**Implementation details:**
1. Modify `_merge_multiple_upstreams` to accept a new internal boolean `is_standalone_projection=False`.
2. If `is_standalone_projection` is true:
   - Calculate `rel_dir` based on the target path relative to the root.
   - Run the upstream `per-file-ignores` table through `_rewrite_per_file_ignores`.
   - After the merge, `del target_config["extend"]`.
3. Modify the `pull` function. After it successfully finishes Phase 1 (syncing the root `to` target), it should check `config.get("standalone_targets")`.
4. If targets exist, iterate over them. For each target, programmatically invoke `merge_ruff_toml` (or equivalent core logic) using the root `to` file as the local upstream, and passing `is_standalone_projection=True`.

### Task 5: End-to-End Integration Test (Complexity: 3/5 - Medium)
**File to modify:** `tests/test_e2e.py` & `tests/lifecycle_tomls/`
**Goal:** Prove the CLI correctly handles Phase 1 and Phase 2 together automatically.

---

## Agent Handoff Recommendations
- **Use an advanced reasoning model** for **Task 2** and **Task 4**. Modifying `tomlkit` proxy tables safely and correctly hooking into the recursive merge pipeline without causing regressions requires deep contextual awareness.
