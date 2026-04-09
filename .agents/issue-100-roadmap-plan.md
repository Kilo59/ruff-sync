# Issue #100 — Feature Roadmap: Ecosystem-Inspired Improvements

> **Source issue**: [#100 Feature roadmap: ecosystem-inspired improvements for ruff-sync](https://github.com/Kilo59/ruff-sync/issues/100)
> **Status**: Planning / Pre-implementation

---

## Overview

Issue #100 surveyed how 8+ ecosystems (ESLint, Prettier, Stylelint, RuboCop, golangci-lint, Cargo/Rust, pre-commit, and Ruff's own `extend`) handle shared linter/formatter config. The result is a **10-item prioritized roadmap** grouped into three tiers:

| Tier | Theme | Items |
|---|---|---|
| 🟢 Tier 1 — High Impact, Natural Extensions | Core capabilities that directly complement the existing merge pipeline | #1 Config Layering, #2 Richer CI drift output, #3 Lock/pin versions |
| 🟡 Tier 2 — Valuable Additions | Ergonomic improvements and power-user features | #4 Dry-run mode, #5 Per-key merge strategies, #6 `status` command, #7 Monorepo support |
| 🔵 Tier 3 — Forward-Looking / Exploratory | Long-lived R&D; high value but high uncertainty | #8 Bidirectional sync/push, #9 Webhook/GitHub App, #10 Config validation |

**Supplemental item**: README ecosystem documentation (adding RuboCop, Stylelint, golangci-lint, Cargo `[workspace.lints]`, pre-commit to the survey table).

---

## Current Architecture (Grounding)

Understanding the existing codebase is essential before proposing changes.

### Key modules

| File | Role |
|---|---|
| `cli.py` | `ArgumentParser` wiring, `Arguments` (NamedTuple), resolution helpers (`_resolve_branch`, `_resolve_upstream`, …), `main()` |
| `core.py` | `fetch_upstream_config`, `merge_ruff_toml`, `_recursive_update`, `pull`, `check`, URL conversion |
| `constants.py` | `ConfKey` enum (TOML keys), `MissingType`/`MISSING` sentinel, `OutputFormat` enum, `resolve_defaults()` |
| `formatters.py` | `ResultFormatter` Protocol; `TextFormatter`, `GithubFormatter`, `JsonFormatter`, `GitlabFormatter`, `SarifFormatter` |
| `pre_commit.py` | Pre-commit hook version sync |
| `config_io.py` | `RuffConfigFileName`, `resolve_target_path`, `is_ruff_toml_file` |

### Configuration contract

```toml
[tool.ruff-sync]
upstream = "https://github.com/org/repo"  # or list[str]
branch   = "main"
path     = ""
exclude  = ["lint.per-file-ignores"]
to       = "."
output-format = "github"
pre-commit-version-sync = true
```

Config is read by `get_config()` (cached), mapped via `ConfKey.get_canonical()`, and resolved in `_resolve_args()`. The `MISSING` sentinel from `constants.py` is the standard way to distinguish "not provided" from explicit defaults.

### CLI exit codes (current)

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Dependency / config error |
| `4` | One or more upstream fetch failures |

---

## Tier 1 — High Impact, Natural Extensions

### 1 — Config Inheritance / Layering (ESLint flat config model)

**Goal**: Allow an ordered list of upstream sources where later entries override earlier ones.

**Current state**: Already partially implemented — `upstream` already accepts `list[str]` and `fetch_upstreams_concurrently` fetches them concurrently, then `_merge_multiple_upstreams` merges sequentially. The fundamental machinery exists.

**Remaining gap**: The original issue's example shows *named* layers with comments, but the existing `upstream = [...]` syntax covers this already. The real user-visible gap is **documentation and discoverability** — users don't know this is possible.

**Implementation notes**:
- No new CLI flags needed. `upstream` already accepts multiple values both via CLI (`ruff-sync pull URL1 URL2`) and config (`upstream = ["URL1", "URL2"]`).
- Verify and add a focused test in `test_e2e.py` that a 3-layer merge resolves precedence correctly (last URL wins on a conflict).
- Update the README and the `ruff-sync-usage` skill with a "layered upstreams" example.

**Scope**: Small — mostly docs + a test.

---

### 2 — Richer CI Drift Output (exit codes + structured formats)

**Goal**: Differentiate exit codes so CI pipelines can distinguish classes of failures. Extend `--output-format` to cover SARIF for code-scanning UIs.

**Current state**:
- `OutputFormat` enum already has `TEXT`, `JSON`, `GITHUB`, `GITLAB`, `SARIF`. Classes `GithubFormatter`, `SarifFormatter`, `GitlabFormatter` all exist in `formatters.py`.
- Exit codes 0, 1, 4 are defined but there is **no dedicated code for "out of sync"** — `check` currently returns `1` for drift.

**Proposed exit code table**:

| Code | Meaning |
|---|---|
| `0` | In sync |
| `1` | Configuration / dependency error |
| `2` | Out of sync (drift detected) |
| `3` | Warning only (e.g. non-fatal upstream issue) |
| `4` | Upstream unreachable / fetch failure |

**Implementation notes**:
- Add `ExitCode` `IntEnum` to `constants.py` (e.g. `OK=0`, `CONFIG_ERROR=1`, `OUT_OF_SYNC=2`, `UPSTREAM_ERROR=4`).
- Update `core.check()` to return `ExitCode.OUT_OF_SYNC` (2) instead of `1` when drift is found.
- Update `main()` return values to use `ExitCode`.
- Update CI docs, `ruff-sync-usage` skill, and the `--output-format` help string.
- Tests: `test_check.py` will need updated expected exit code assertions.

> [!IMPORTANT]
> This is technically a **breaking change** for any CI script that checks `[ $? -eq 1 ]` for drift. Document the migration clearly in the changelog and consider a deprecation period where both `1` and `2` are valid for a release.

**Scope**: Medium — touches `constants.py`, `core.py`, `cli.py`, several tests.

---

### 3 — Lock / Pin Upstream Versions

**Goal**: Record the exact commit SHA fetched from an upstream so subsequent `check` runs can verify against the same snapshot.

**Inspiration**: `npm package-lock.json`, `go.sum`, pre-commit's `rev:` pinning.

**Proposed design**:

```toml
# Written by `ruff-sync pull --lock` or automatically with `save = true`
[tool.ruff-sync.lock]
"https://github.com/my-org/standards" = "abc1234def5678"  # SHA resolved at pull time
pulled-at = "2026-03-10T14:30:00Z"
```

Or a standalone `ruff-sync.lock` file (simpler to gitignore independently).

**Implementation notes**:
- `fetch_upstream_config` returns a `FetchResult(buffer, resolved_upstream)`. Extend it with an optional `sha: str | None` field (add `sha` to the `NamedTuple`).
- For HTTP sources: resolve SHA via GitHub API (`/repos/{owner}/{repo}/commits?path=pyproject.toml&per_page=1`) if `GITHUB_TOKEN` is set; otherwise store the ETag.
- For git sources (`_fetch_via_git`): after `git clone --depth 1`, run `git rev-parse HEAD` to capture the exact SHA.
- Add `ruff-sync update` sub-command that bumps the lock to latest.
- `check` without a lock behaves as today; `check --locked` validates against the locked SHA.

> [!WARNING]
> HTTP ETag-based pinning is less reliable than SHA pinning. Make the limitation clear in docs. Recommend using git:// URLs for true reproducibility.

**Scope**: Large — new `FetchResult` field, new lock file I/O, new `update` subcommand, CI integration docs.

---

## Tier 2 — Valuable Additions

### 4 — Dry-run / Preview Mode

**Goal**: `pull --dry-run` prints the fully merged TOML to stdout without writing it to disk.

**Current state**: `check --diff` shows a unified diff but doesn't print the full merged file. There is no `pull --dry-run`.

**Implementation notes**:
- Add `--dry-run` flag to the `pull` subparser in `cli.py`.
- In `core.pull()`, after computing `merged_doc`, if `args.dry_run` is `True`, write to stdout (`sys.stdout`) instead of the target file.
- The `Arguments` NamedTuple needs a `dry_run: bool = False` field.
- Add `ConfKey.DRY_RUN = "dry-run"` to `ConfKey` if it should be saveable to config (probably not — leave it CLI-only).

**Inspiration**: `terraform plan`, `npm pack --dry-run`.

**Scope**: Small-to-medium.

---

### 5 — Per-Key Merge Strategies

**Goal**: Support different merge behaviors per TOML key instead of the current "always overwrite" default.

**Proposed strategies**:

| Strategy | Behaviour |
|---|---|
| `replace` (default) | Upstream value completely replaces local value |
| `append` | For list values: append upstream items to local list (e.g. `lint.extend-select`) |
| `local-only` | Never touch this key (effectively an exclude per-key) |
| `local-first` | Use local value if present, otherwise use upstream |

**Config syntax proposal**:

```toml
[tool.ruff-sync.merge-strategy]
"lint.extend-select" = "append"
"target-version" = "local-only"
```

**Implementation notes**:
- Add `merge_strategy: dict[str, str]` to `Config` TypedDict.
- Add `ConfKey.MERGE_STRATEGY = "merge-strategy"` to `ConfKey`.
- Create `MergeStrategy` enum in `constants.py`: `REPLACE`, `APPEND`, `LOCAL_ONLY`, `LOCAL_FIRST`.
- Modify `_recursive_update` (in `core.py`) to accept an optional `merge_strategies: Mapping[str, MergeStrategy]` parameter. The dotted key path (e.g. `lint.extend-select`) is used to look up the strategy.
- The `exclude` mechanism could be unified with `local-only` as a migration convenience.

**Scope**: Medium-to-large — changes the core merge algorithm, new `ConfKey`, new tests in `test_corner_cases.py`.

---

### 6 — `status` Command — Richer Sync Reporting

**Goal**: A human-readable summary of the current sync state, including upstream SHA, last-pulled time, and per-tool drift summary.

**Proposed output**:

```
ruff-sync v0.2.0
upstream:  https://github.com/my-org/standards (main @ abc1234)
target:    pyproject.toml
ruff       ✅ in sync        (last pulled: 2026-03-10)
mypy       ❌ out of sync    (3 keys differ)
```

**Implementation notes**:
- `status` is a new subcommand in `cli.py` (beside `pull`, `check`, `inspect`).
- Requires the lock file (Feature #3) to report the "last pulled" timestamp and pinned SHA.
- For the drift summary: run the same diff logic as `check` but in summary-only mode (count of differing keys, not full diff text).
- If no lock exists, report "unknown" for last-pulled but still show drift status.

**Scope**: Medium — depends on #3 for full value, but the drift-count part can be built independently.

---

### 7 — Monorepo Support

**Goal**: Allow a single `pyproject.toml` at the repo root to configure independent sync targets for multiple sub-packages.

**Proposed config**:

```toml
[[tool.ruff-sync.targets]]
to = "packages/api"
exclude = ["lint.per-file-ignores"]

[[tool.ruff-sync.targets]]
to = "packages/worker"
exclude = ["target-version"]
```

**Implementation notes**:
- Add support for `[[tool.ruff-sync.targets]]` TOML array of tables.
- Each target entry inherits top-level `upstream`, `branch`, etc. unless overridden.
- `cli.py`'s `get_config()` and `_resolve_args()` would need to expand into a list of `Arguments` objects when targets are present.
- `pull` and `check` would iterate over all targets.
- This is a significant schema change — design carefully for backward compatibility.

> [!IMPORTANT]
> This is the largest Tier 2 item. Consider making it an ADR before implementation.

**Scope**: Large.

---

## Tier 3 — Forward-Looking / Exploratory

These are exploratory. Opening tracking issues is appropriate, but full implementation plans should come later.

### 8 — Bidirectional Sync / Push Command

Push local changes upstream as a GitHub/GitLab PR. Very high value for teams making downstream discoveries.

**Implementation notes sketch**:
- Requires authenticated GitHub API access (`GITHUB_TOKEN`).
- Would create a branch on the upstream repo with the locally changed `[tool.ruff]` section, then open a PR.
- Scope: Very Large. Dependencies: git auth, PR API, fork/branch strategy.

---

### 9 — Webhook / GitHub App for Automatic PRs

A hosted service (like Renovate or Dependabot) that watches upstream config repos and opens PRs downstream when upstream changes.

**Notes**: This is out of scope for the `ruff-sync` CLI itself — it's a service/infrastructure concern. Could be built as a separate GitHub App or Action. The CLI's `check` exit codes (#2 above) are a prerequisite.

---

### 10 — Config Validation

Before applying a merge, validate the merged result:
- Warn if upstream references deprecated Ruff rules (query `ruff rule --all` or maintain a list).
- Warn if `target-version` conflicts with local `requires-python`.
- Optionally run `ruff check --no-fix` against the merged config to catch syntax errors.

**Implementation notes sketch**:
- Add a `validate` step inside `pull()` (between merge and write).
- Integrate with `ruff` subprocess (similar to how `pre_commit.py` calls subprocess tools).
- This overlaps with the `ruff-inspect` TUI — the TUI already shows per-rule status.

---

## Supplemental — README Ecosystem Documentation

Update the "How Other Ecosystems Solve This" README section to include:

| Tool | Mechanism | Notable feature |
|---|---|---|
| RuboCop (Ruby) | `inherit_from: <URL>` | Native remote URL — closest peer to ruff-sync |
| Stylelint (CSS) | `extends` via npm packages | Package-based distribution |
| golangci-lint (Go) | No native remote config | Teams use CI workarounds |
| Cargo/Rust | `[workspace.lints]` | Monorepo only, no remote |
| pre-commit | No `include`/`extends` | Repos must duplicate config |

---

## Recommended Sequencing

The items above are not all equal in effort or dependency. Here is a recommended order:

```
Phase 0 (docs/quick wins):
  - #1 Layered Upstreams — docs + test only
  - README ecosystem table

Phase 1 (CI hardening):
  - #2 Exit code differentiation + ExitCode enum

Phase 2 (ergonomics):
  - #4 Dry-run mode (small, high user value)
  - #6 Status command (lite version without lock)

Phase 3 (advanced features):
  - #3 Lock file + `update` subcommand
  - #6 Status command (full version with lock)
  - #5 Per-key merge strategies

Phase 4 (monorepo):
  - #7 Monorepo targets — design ADR first

Phase 5 (exploratory / long-term):
  - #10 Config validation
  - #8 Bidirectional push
  - #9 Webhook/GitHub App (external service)
```

---

## Open Questions / Design Decisions

> [!IMPORTANT]
> These need answers before starting Phase 2–3 work.

1. **Lock file location**: `[tool.ruff-sync.lock]` (inside `pyproject.toml`) vs. a separate `ruff-sync.lock` file? A standalone file is easier to gitignore and diff-track, but adds a new file to every user's repo.

2. **Exit code migration**: Should drift remain `1` for one more release cycle (with a deprecation warning) before moving to `2`? This minimizes breakage for existing CI pipelines.

3. **`merge-strategy` syntax**: The dotted-key syntax (e.g. `"lint.extend-select" = "append"`) is readable but unusual for TOML. Alternative: an explicit array-of-tables with `key`, `strategy` fields. Which is more ergonomic?

4. **`status` without a lock**: Should `status` fail loudly if no lock exists, or silently omit the "last pulled" field?

5. **Monorepo schema backward compat**: The `[[tool.ruff-sync.targets]]` array-of-tables would coexist with top-level `upstream`, `to`, etc. What is the exact precedence rule? Should scalar `to` continue to work if `targets` is present?

---

## Testing Strategy (per feature)

| Feature | Primary test file(s) | Notes |
|---|---|---|
| #1 Layered upstreams | `test_e2e.py`, `test_corner_cases.py` | New lifecycle triple: base + domain → final |
| #2 Exit codes | `test_check.py`, `test_ci_integration.py` | Update expected return codes |
| #3 Lock file | New `test_lock.py` | `pyfakefs` for file I/O; `respx` for ETag mocking |
| #4 Dry-run | `test_basic.py`, `test_e2e.py` | Assert stdout contains merged TOML, file unchanged |
| #5 Merge strategies | `test_corner_cases.py` | `append`, `local-only`, `local-first` strategies |
| #6 Status | New `test_status.py` | Mocked upstream + lock file |
| #7 Monorepo | New `test_monorepo.py` | Multiple `pyfakefs` directories |
| #10 Config validation | New `test_validation.py` | Deprecated rule detection |

---

## Related Issues

- [#69](https://github.com/Kilo59/ruff-sync/issues/69) — Multi-tool config sync (overlaps with Tier 1 scope expansion)
- [#74](https://github.com/Kilo59/ruff-sync/issues/74) — Short CLI aliases (more useful if multi-tool lands)
- [#83](https://github.com/Kilo59/ruff-sync/issues/83) — Example Ruff configs for various domains (Tier 2)
- [#87](https://github.com/Kilo59/ruff-sync/issues/87) — Example config: Data Science / Data Engineering (Tier 2)
