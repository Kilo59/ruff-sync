# CI Integration Recipes

## GitHub Actions

### Basic Drift Check

Add this step to any existing workflow (e.g., `.github/workflows/ci.yaml`):

```yaml
- name: Check Ruff config is in sync
  run: ruff-sync check --semantic --output-format github
```

`--semantic` ignores cosmetic differences (comments, whitespace) — only real value or rule changes cause failure.
`--output-format github` creates inline PR annotations for errors and warnings.

### Full Workflow Example

Uses [`astral-sh/setup-uv`](https://github.com/astral-sh/setup-uv) — the official action that installs uv, adds it to PATH, and handles caching. No separate `setup-python` step needed.

```yaml
name: Ruff sync check

on:
  push:
    branches: [main]
  pull_request:

jobs:
  ruff-sync-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v6
        with:
          version: "0.10.x"   # pin to a minor range; Dependabot can keep this current

      - name: Install ruff-sync
        run: uv tool install ruff-sync

      - name: Check Ruff config is in sync with upstream
        run: ruff-sync check --semantic --output-format github
```

### With Pre-commit Sync Check

To also verify the pre-commit hook version, add the `--pre-commit` flag. Any non-zero exit code (1 = config drift, 2 = stale hook rev) will fail the CI step:

```yaml
- name: Check Ruff config and pre-commit hook
  run: ruff-sync check --semantic --pre-commit --output-format github
```

(Note: For better consistency, you can instead set `pre-commit-version-sync = true` in your `pyproject.toml` — then `ruff-sync check --semantic` will automatically include this check.)

---

## GitLab CI

Use the official [`ghcr.io/astral-sh/uv`](https://docs.astral.sh/uv/guides/integration/gitlab/) image — uv is already on the `PATH`, no install step needed.

```yaml
variables:
  UV_VERSION: "0.10"
  PYTHON_VERSION: "3.12"
  BASE_LAYER: bookworm-slim
  UV_LINK_MODE: copy   # required: GitLab mounts build dir separately

ruff-sync-check:
  stage: lint
  image: ghcr.io/astral-sh/uv:$UV_VERSION-python$PYTHON_VERSION-$BASE_LAYER
  script:
    - uv tool install ruff-sync
    - ruff-sync check --semantic
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == "main"'
```

---

## Pre-commit Hook

Run `ruff-sync check` as a pre-commit hook to catch drift before every commit:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/Kilo59/ruff-sync
  rev: v0.1.0   # pin to a release tag
  hooks:
    - id: ruff-sync-check
```

The hook runs `ruff-sync check --semantic` automatically. Update `rev` to the latest ruff-sync version.

---

## Makefile

```makefile
.PHONY: sync-check sync

sync-check:
	ruff-sync check --semantic

sync:
	ruff-sync
	git diff pyproject.toml
```

---

## Deciding: `--semantic` vs. Full String Check

| Mode | Fails on | Use when |
|------|---------|---------|
| `ruff-sync check --semantic` | Value/rule differences only | CI — avoids false positives from local comment edits |
| `ruff-sync check` | Any string difference (comments, whitespace, values) | Enforcing exact config file consistency |

Recommendation: **use `--semantic` in CI** and save the full-string check for auditing purposes.

---

## Dogfooding (Self-Check)

If `ruff-sync` is configured in the project's own `pyproject.toml` (the standard case), just run:

```bash
ruff-sync check
```

No URL argument needed — it reads `upstream` from `[tool.ruff-sync]`.
