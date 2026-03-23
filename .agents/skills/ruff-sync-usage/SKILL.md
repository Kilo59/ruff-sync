---
name: ruff-sync-usage
description: >-
  Configure and operate ruff-sync to synchronize Ruff linter settings across Python projects.
  Use when the user wants to set up ruff-sync, sync Ruff config from an upstream source,
  check for configuration drift, integrate ruff-sync into CI, troubleshoot sync issues,
  or keep Ruff rules consistent across multiple repositories.
---

# ruff-sync Usage

`ruff-sync` pulls a canonical Ruff configuration from an upstream URL and merges it into your local project, preserving comments, whitespace, and per-project overrides.

## Quick Start

```bash
# 1. Install
uv tool install ruff-sync

# 2. Sync from an upstream repo (extracts [tool.ruff] / ruff.toml automatically)
ruff-sync https://github.com/my-org/standards

# 3. Review the changes before committing
git diff pyproject.toml
```

## Persist Configuration

Add to `pyproject.toml` so you don't need to pass CLI args every time:

```toml
[tool.ruff-sync]
upstream = "https://github.com/my-org/standards"
exclude = [
    "target-version",            # each project uses its own Python version
    "lint.per-file-ignores",     # project-specific suppressions
    "lint.ignore",
    "lint.isort.known-first-party",
]
```

Then just run `ruff-sync` (no arguments needed).

See [references/configuration.md](references/configuration.md) for all config keys and defaults.

## Common Workflows

### Initial Project Setup

```
Setup Progress:
- [ ] 1. Install ruff-sync (uv tool install ruff-sync)
- [ ] 2. Add [tool.ruff-sync] to pyproject.toml with upstream URL and exclusions
- [ ] 3. Run `ruff-sync` to pull the upstream config
- [ ] 4. Review `git diff pyproject.toml`
- [ ] 5. Fix any new lint errors: `uv run ruff check . --fix`
- [ ] 6. Commit
```

### Upstream Layers (multi-source)

Stack multiple upstream sources — later entries win on conflict:

```toml
[tool.ruff-sync]
upstream = [
    "https://github.com/my-org/python-standards",   # base company rules
    "https://github.com/my-org/ml-team-tweaks",     # team-specific overrides
]
```

### CI Drift Check

```
CI Setup Progress:
- [ ] 1. Add ruff-sync check step to CI workflow (see references/ci-integration.md)
- [ ] 2. Decide: --semantic for value-only checks, or full string comparison
- [ ] 3. Set exit-code expectations (0 = in sync, 1 = config drift, 2 = pre-commit only)
- [ ] 4. Verify locally: `ruff-sync check --semantic`
```

### Pre-commit Hook Sync

Keep the `ruff-pre-commit` hook version in `.pre-commit-config.yaml` aligned with the project's Ruff version:

```toml
[tool.ruff-sync]
pre-commit-version-sync = true
```

Then run `ruff-sync` — it updates the hook rev automatically. Exit code 2 means only the hook version is out of sync (Ruff config itself is fine).

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | In sync — no action needed |
| `1` | Ruff config is out of sync with upstream |
| `2` | Config is in sync, but pre-commit hook version is stale (only when `--pre-commit` is active) |

## URL Formats Supported

All of these work as the `upstream` value:

```bash
ruff-sync https://github.com/my-org/standards              # repo root
ruff-sync https://github.com/my-org/standards/tree/main/cfg  # subdirectory
ruff-sync https://github.com/my-org/standards/blob/main/ruff.toml  # specific file
ruff-sync https://raw.githubusercontent.com/my-org/standards/main/pyproject.toml
ruff-sync git@github.com:my-org/standards.git             # SSH (shallow clone)
```

## Gotchas

- **`exclude` uses dotted paths, not TOML paths.** `lint.per-file-ignores` refers to the `per-file-ignores` key inside `[tool.ruff.lint]`. Do NOT write `tool.ruff.lint.per-file-ignores`.
- **Use `--init` only for new projects.** `ruff-sync` requires an existing `pyproject.toml` or `ruff.toml`. Pass `--init` to scaffold one if the directory is empty.
- **`--semantic` ignores comments and whitespace.** Use it in CI to avoid false positives from cosmetic local edits. Omit it for strict byte-for-byte checks.
- **SSH URLs trigger a shallow clone.** `git@github.com:...` URLs use `git clone --filter=blob:none --depth=1` — no `git` credential issues as long as SSH auth is configured.
- **Later upstreams win in `upstream` lists.** In a multi-source list, keys set by entry 2 overwrite keys from entry 1.
- **Pre-commit exit code 2 is intentional.** A `2` exit from `ruff-sync check` means the Ruff _config_ is fine, only the pre-commit hook tag is stale. You may want to treat this differently from a full config drift (exit 1) in CI.

## References

- **[Configuration reference](references/configuration.md)** — All `[tool.ruff-sync]` keys, types, and defaults
- **[Troubleshooting](references/troubleshooting.md)** — Common errors and how to resolve them
- **[CI integration recipes](references/ci-integration.md)** — GitHub Actions, GitLab CI, pre-commit hook
