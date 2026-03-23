# CI Integration Recipes

## GitHub Actions

### Basic Drift Check

Add this step to any existing workflow (e.g., `.github/workflows/ci.yaml`):

```yaml
- name: Check Ruff config is in sync
  run: ruff-sync check --semantic
```

`--semantic` ignores cosmetic differences (comments, whitespace) — only real value or rule changes cause failure.

### With ruff-sync Installed via uv

If ruff-sync is not part of your project's dev dependencies, install it inline:

```yaml
- name: Install ruff-sync
  run: uv tool install ruff-sync

- name: Check Ruff config is in sync
  run: ruff-sync check --semantic
```

### Full Workflow Example

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

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Install ruff-sync
        run: uv tool install ruff-sync

      - name: Check Ruff config is in sync with upstream
        run: ruff-sync check --semantic
```

### With Pre-commit Sync Check

To also verify the pre-commit hook version, add `--pre-commit`. Any non-zero exit code (1 = config drift, 2 = stale hook rev) will fail the CI step:

```yaml
- name: Check Ruff config and pre-commit hook
  run: ruff-sync check --semantic --pre-commit
```

If you don't want to enforce hook version sync, simply omit `--pre-commit`.

---

## GitLab CI

```yaml
ruff-sync-check:
  stage: lint
  image: python:3.12-slim
  before_script:
    - pip install uv
    - uv tool install ruff-sync
  script:
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
