# Documentation Update Plan (post-v0.1.5)

> **Context**: This plan covers documentation improvements needed after the v0.1.5 release. Changes since that release include: config validation (`--validate`), strict mode (`--strict`), Python version consistency checks, deprecated rule detection, a new `validation.py` module, `ExecutionArgs` refactoring, and boolean flag persistence (`validate` and `strict` in `[tool.ruff-sync]`).
>
> Some documentation was partially updated alongside the code changes (usage.md, README.md, configuration.md got the basics). This plan addresses remaining gaps and general improvements.

---

## Task 1: Add `validate` and `strict` to Configuration Reference Table

**File**: `docs/configuration.md`
**Lines**: 7–16 (the reference table)

**What to do**: Add two new rows to the reference table for the `validate` and `strict` configuration keys. These keys were added to `Config` TypedDict and `ConfKey` enum but are missing from the documentation reference table.

**Add these rows** after the `pre-commit-version-sync` row (line 16):

```markdown
| `validate` | `bool` | `false` | Run the merged config through Ruff before writing to disk. Aborts the sync if Ruff rejects the config. |
| `strict` | `bool` | `false` | Treat validation warnings (version mismatches, deprecated rules) as hard failures. Implies `validate = true`. |
```

**Why**: Users who configure via `pyproject.toml` (not CLI) have no documentation showing these keys exist in the config reference.

---

## Task 2: Add Validation Config Example to Configuration Page

**File**: `docs/configuration.md`
**Location**: After the "Preserve target version" section (after line 66) and before "Sequential merging"

**What to do**: Add a new example subsection showing how to enable validation persistently via config:

```markdown
#### Enable validation by default

If you always want the merged config validated before writing, enable it in your configuration:

\`\`\`toml
[tool.ruff-sync]
validate = true
\`\`\`

For even stricter enforcement (treat warnings like Python version mismatches and deprecated rules as hard failures):

\`\`\`toml
[tool.ruff-sync]
strict = true  # implies validate = true
\`\`\`
```

**Why**: The existing docs only show `--validate` and `--strict` as CLI flags. Users should know they can persist these settings.

---

## Task 3: Add Validation to CI Integration Examples

**File**: `docs/ci-integration.md`
**Location**: After the "Basic Check" section (after line 30), add a new subsection

**What to do**: Add a new subsection showing how to combine `check` with `--validate`/`--strict` in CI workflows. Insert the following after line 36 (after the annotation note):

```markdown
#### With Validation

To catch broken or deprecated Ruff configuration during CI, add `--strict` to upgrade validation warnings into failures:

\`\`\`yaml
name: "Standards Check"

on:
  pull_request:
    branches: [main]

jobs:
  ruff-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Check Ruff Config
        run: uvx ruff-sync check --semantic --strict --output-format github
\`\`\`

> [!TIP]
> `--strict` implies `--validate`. You do not need to pass both flags. This will catch deprecated Ruff rules and Python version mismatches in addition to configuration drift.
```

**Why**: CI is the most important place to use validation, and there's no CI example showing it.

---

## Task 4: Add Validation to Automated Sync PR Workflow

**File**: `docs/ci-integration.md`
**Location**: Inside the "Automated Sync PRs" YAML example (line 83)

**What to do**: Update the `run: uvx ruff-sync` line to include `--validate`:

```yaml
      - name: Pull upstream
        run: uvx ruff-sync --validate
```

**Why**: When auto-syncing, you want to catch broken configs before they are committed. A simple one-word addition that significantly improves the example.

---

## Task 5: Add Exit Code for Validation Failure

**File**: `docs/ci-integration.md`
**Location**: Exit Codes table (lines 150–156)

**What to do**: Check the source code to confirm whether validation failures use an existing exit code or a new one. Based on the current code, `pull()` returns `1` when validation fails. Update the exit code table to clarify this:

Update the row for exit code `1` to explicitly mention validation:

```markdown
| **1** | Config drift (`check`), validation failure (`pull --validate`), or sync error |
```

**Why**: Users need to understand what exit code to expect when validation blocks a sync.

---

## Task 6: Update Pre-commit Hook Versions

**File**: `docs/pre-commit.md`
**Lines**: 15, 26, 43, 45

**What to do**: Update all `rev: v0.1.3` references to `rev: v0.1.5` (or whatever the latest release is). There are four occurrences.

Search for `v0.1.3` in the file and replace with `v0.1.5`.

**Why**: The pre-commit docs reference an outdated version. Users who copy-paste these examples get an old version.

---

## Task 7: Update Pre-defined Configs Page Versions

**File**: `docs/pre-defined-configs.md`
**Lines**: 42, 80, 118

**What to do**: Update all `--branch v0.1.3` references to `--branch v0.1.5`.

Search for `v0.1.3` in the file and replace with `v0.1.5`.

**Why**: Same reason as Task 6 — hardcoded old version in examples.

---

## Task 8: Add Validation Troubleshooting Entries

**File**: `docs/troubleshooting.md`
**Location**: After the "Merge conflicts in TOML" section (after line 47), before "Multi-upstream Fetch Failures"

**What to do**: Add three new troubleshooting entries:

```markdown
### Validation failed: `ruff` not found

**Warning**: `⚠️  \`ruff\` not found on PATH — skipping Ruff config validation.`

**Solution**: This is a soft warning, not a failure. If you explicitly want validation, ensure `ruff` is installed and available on your PATH. If using `uv`, run `uv pip install ruff` or add it to your project's dependencies.

### Python version mismatch

**Warning**: `⚠️  Version mismatch: upstream [tool.ruff] target-version='py39'...`

**Solution**:
This means the upstream configuration targets a different Python version than your project's `requires-python`. You have three options:

1. **Update upstream**: Coordinate with your team to update the upstream `target-version`.
2. **Exclude the key**: Add `target-version` to your `exclude` list to manage it locally.
3. **Ignore the warning**: In non-strict mode, this is informational only and does not block the sync.

In `--strict` mode, this warning becomes a hard failure. See the [Usage Guide](usage.md#validating-before-writing) for details.

### Deprecated rule detected

**Warning**: `⚠️  Upstream config uses deprecated rule 'XXX'...`

**Solution**:
The upstream configuration references a Ruff rule that has been deprecated. This often happens when the upstream hasn't been updated after a Ruff version bump.

1. **Update upstream**: Replace the deprecated rule with its successor in the upstream config.
2. **Ignore the warning**: In non-strict mode, deprecated rules are informational warnings only.

In `--strict` mode, deprecated rules cause a hard failure.
```

**Why**: The troubleshooting page has no entries for the new validation features. Users encountering these messages for the first time need guidance.

---

## Task 9: Update Index Page Feature List

**File**: `docs/index.md`
**Location**: The "🚀 Key Features" bullet list (lines 13–24)

**What to do**: Add a new bullet for config validation after the "CI Ready" bullet (line 22):

```markdown
* **✅ Config Validation**: Optionally validate merged configs with Ruff before writing. Strict mode catches deprecated rules and Python version mismatches.
```

**Why**: The index page feature list is the first thing users see. The new validation capability is a significant feature that should be highlighted.

---

## Task 10: Update Advanced Config Example with Validation Keys

**File**: `docs/examples/advanced-config.toml`
**Location**: After line 15 (before the closing of the file)

**What to do**: Add the `validate` key to the advanced example to showcase it as a recommended practice:

```toml
# Validate merged config before writing (catches bad upstream changes)
validate = true
```

**Why**: The example files serve as copy-paste templates. Including `validate` in the advanced example normalizes its usage.

---

## Task 11: Add `--no-validate` and `--no-strict` to Command Reference

**File**: `docs/usage.md`
**Location**: Command Reference section, specifically the `--validate` and `--strict` entries (lines 192–193)

**What to do**: Update the descriptions to mention the `--no-*` variants, since these use `BooleanOptionalAction`:

Line 192, update `--validate` entry:
```markdown
* **`--validate` / `--no-validate`**: Run the merged config through Ruff before writing to disk. If Ruff rejects the config (e.g., due to an unknown key), the sync is aborted and the local file is left unchanged. Off by default. Use `--no-validate` to explicitly disable validation even if `validate = true` is set in your config.
```

Line 193, update `--strict` entry:
```markdown
* **`--strict` / `--no-strict`**: Treat validation warnings (such as Python version mismatches or deprecated rules) as hard failures. Implies `--validate` — you do not need to pass both flags. Use `--no-strict` to explicitly disable strict mode even if `strict = true` is in config.
```

**Why**: The CLI actually supports `--no-validate` and `--no-strict` (via `BooleanOptionalAction`), but the docs don't mention them. Users who set `validate = true` in their config need to know how to opt out for a specific run.

---

## Task 12: Update Agent Skill Configuration Reference

**File**: `.agents/skills/ruff-sync-usage/references/configuration.md`
**Location**: After the `pre-commit-version-sync` section (after line 101, before "Full Example")

**What to do**: Add two new sections for `validate` and `strict`:

```markdown
---

### `validate` *(default: `false`)*

When `true`, `ruff-sync` validates the merged configuration by running it through Ruff before writing to disk. If Ruff rejects the config (e.g., due to an unknown key), the sync is aborted and the local file is left unchanged.

\`\`\`toml
validate = true
\`\`\`

> [!NOTE]
> Validation requires `ruff` to be available on PATH. If `ruff` is not found, validation is skipped with a warning.

---

### `strict` *(default: `false`)*

When `true`, all validation warnings (Python version mismatches, deprecated rules) are treated as hard failures. Implies `validate = true`.

\`\`\`toml
strict = true
\`\`\`
```

Also update the "Full Example" block to include these keys:

```toml
[tool.ruff-sync]
upstream = [
    "https://github.com/my-org/python-standards",
    "https://github.com/my-org/backend-team-rules",
]
exclude = [
    "target-version",
    "lint.per-file-ignores",
    "lint.ignore",
    "lint.isort.known-first-party",
]
branch = "main"
path = "ruff"
to = "."
pre-commit-version-sync = true
validate = true
```

**Why**: The agent skill's configuration reference is supposed to be the authoritative reference for AI agents. It currently has no mention of `validate` or `strict` as config keys.

---

## Task 13: Update Agent Skill CI Reference with Validation

**File**: `.agents/skills/ruff-sync-usage/references/ci-integration.md`
**Location**: After the "Basic Drift Check" section (after line 15)

**What to do**: Add a note about combining check + validation:

```markdown
### With Strict Validation

To also catch deprecated rules and Python version mismatches in CI:

\`\`\`yaml
- name: Check Ruff config (with validation)
  run: ruff-sync check --semantic --strict --output-format github
\`\`\`

`--strict` implies `--validate`. Deprecated rules and version mismatches are upgraded to failures.
```

**Why**: Keeps the agent skill CI reference in sync with the main docs.

---

## Task 14: Update Pre-commit Skill References

**File**: `.agents/skills/ruff-sync-usage/references/ci-integration.md`
**Lines**: 166

**What to do**: Update `rev: v0.1.3` to `rev: v0.1.5`.

**Why**: Same version staleness issue as the main docs.

---

## Task 15: Add FAQ Entry for Validation

**File**: `docs/troubleshooting.md`
**Location**: FAQ section (after line 85)

**What to do**: Add two new FAQ entries:

```markdown
### Does `--validate` require `ruff` to be installed?

Yes, validation shells out to the `ruff` binary. If `ruff` is not on your `PATH`, validation is silently skipped with a warning. To use validation, ensure Ruff is installed (e.g., via `uv pip install ruff` or as a project dependency).

### What does `--strict` check for?

In addition to the basic config syntax validation from `--validate`, `--strict` upgrades the following warnings to hard failures:

1. **Python version mismatch**: The upstream `target-version` doesn't align with your local `requires-python`.
2. **Deprecated Ruff rules**: Any rule codes in `lint.select`, `lint.ignore`, `lint.extend-select`, `lint.extend-ignore`, or `lint.extend-fixable` that Ruff reports as deprecated.
3. **Ruff stderr warnings**: Any warning messages Ruff emits to stderr when parsing the config.
```

**Why**: These are the most likely questions users will have about the new features.

---

## Execution Order

> [!IMPORTANT]
> Tasks can be executed in any order. They are independent of each other. However, a logical grouping would be:
>
> 1. **Core docs** (Tasks 1-5, 9, 11) — Configuration, usage, CI, and index pages
> 2. **Version bumps** (Tasks 6-7, 14) — Simple find-and-replace of `v0.1.3` → `v0.1.5`
> 3. **Troubleshooting** (Tasks 8, 15) — New entries for validation-related issues
> 4. **Examples** (Task 10) — Updated advanced config example
> 5. **Agent skill** (Tasks 12-13) — Keep the AI skill references current

## Validation

After all changes, run:

```bash
uv run mkdocs build --strict 2>&1 | head -50
```

This will catch any broken links, missing files, or Markdown syntax errors in the documentation. Fix any warnings before considering the task complete.
