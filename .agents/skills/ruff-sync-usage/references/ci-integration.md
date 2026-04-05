# CI Integration Recipes

## GitHub Actions

### Basic Drift Check

Add this step to any existing workflow (e.g., `.github/workflows/ci.yaml`):

```yaml
- name: Check Ruff config is in sync
  run: ruff-sync check --semantic --output-format github
```

`--semantic` ignores cosmetic differences (comments, whitespace) — only real value or rule changes cause failure.
`--output-format github` creates inline PR annotations and a structured Job Summary report.

> [!TIP]
> `ruff-sync` automatically groups multiple drifts in the same file into a single annotation to reduce PR noise.

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

To also verify the pre-commit hook version, add the `--pre-commit` flag:

```yaml
- name: Check Ruff config and pre-commit hook
  run: ruff-sync check --semantic --pre-commit --output-format github
```

(Note: For better consistency, you can instead set `pre-commit-version-sync = true` in your `pyproject.toml` — then `ruff-sync check --semantic` will automatically include this check.)

### SARIF Upload (GitHub Advanced Security)

For repositories with GitHub Advanced Security enabled, upload SARIF results to track drift findings in the **Security tab** and get per-key inline PR annotations that persist across runs:

```yaml
- name: Check Ruff config (SARIF)
  run: ruff-sync check --output-format sarif > ruff-sync.sarif || true

- name: Upload SARIF results
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: ruff-sync.sarif
    category: ruff-sync
```

The `|| true` ensures the upload step always runs even when `ruff-sync` exits 1 (drift detected). Without it, GitHub Actions would skip the upload step on failure.

> **Why SARIF over `--output-format github`?**
>
> | Feature | `github` | `sarif` |
> |---------|----------|---------|
> | **PR Feedback** | Inline annotations (grouped) | Inline annotations (per-key) |
> | **Job Summary** | ✅ Markdown table | ❌ (requires separate parsing) |
> | **Persistence** | Ephemeral (until re-run) | Persistent (Security tab) |
> | **Tracking** | Manual | Automated "introduced/resolved" |

---

## GitLab CI

Use the official [`ghcr.io/astral-sh/uv`](https://docs.astral.sh/uv/guides/integration/gitlab/) image — uv is already on the `PATH`, no install step needed.

```yaml
variables:
  UV_VERSION: "0.10"
  PYTHON_VERSION: "3.12"
  BASE_LAYER: alpine
  UV_LINK_MODE: copy   # required: GitLab mounts build dir separately

ruff-sync-check:
  stage: lint
  image: ghcr.io/astral-sh/uv:$UV_VERSION-python$PYTHON_VERSION-$BASE_LAYER
  script:
    - uvx ruff-sync check --semantic --output-format gitlab > gl-code-quality-report.json
  artifacts:
    when: always
    reports:
      codequality: gl-code-quality-report.json
    paths:
      - gl-code-quality-report.json
    expire_in: 1 week
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    - if: '$CI_COMMIT_BRANCH == "main"'
```

### GitLab SAST Report / SARIF (Ultimate tier)

Use `--output-format sarif` to feed the GitLab [Security & Compliance dashboard](https://docs.gitlab.com/user/application_security/) via the `sast` artifact report type:

```yaml
variables:
  UV_VERSION: "0.10"
  PYTHON_VERSION: "3.12"
  BASE_LAYER: alpine
  UV_LINK_MODE: copy   # required: GitLab mounts build dir separately

ruff-sync-sarif:
  stage: lint
  image: ghcr.io/astral-sh/uv:$UV_VERSION-python$PYTHON_VERSION-$BASE_LAYER
  script:
    - uvx ruff-sync check --output-format sarif > ruff-sync.sarif
  artifacts:
    when: always          # Upload even when ruff-sync exits 1 (drift detected)
    reports:
      sast: ruff-sync.sarif
    paths:
      - ruff-sync.sarif
    expire_in: 1 week
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

> **Why SARIF over `--output-format gitlab` (codequality)?**
>
> | Concern | `codequality` | `sarif` |
> |---------|--------------|--------|
> | GitLab tier | Free (MR widget), Ultimate (inline diff) | Ultimate (Security dashboard) |
> | GitHub support | ❌ | ✅ via `upload-sarif` |
> | Per-key findings | ❌ one issue per file | ✅ one finding per drifted TOML key |
> | Finding persistence | MR widget only | Security tab, tracked across branches |
> | Portability | GitLab only | GitHub, GitLab, SonarQube, IDE extensions |
>
> **Rule of thumb**: use `codequality` for lightweight GitLab-native linting feedback; use `sarif` when you need cross-platform compatibility or want findings tracked in a security/code-scanning dashboard.

---

## Pre-commit Hook

Run `ruff-sync check` as a pre-commit hook to catch drift before every commit:

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/Kilo59/ruff-sync
  rev: v0.1.3   # pin to a release tag
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

---

## Exit Codes

| Code | Meaning |
|------|----------|
| **0** | In sync — no drift detected |
| **1** | Config drift — `[tool.ruff]` values differ from upstream |
| **2** | CLI usage error — invalid arguments (reserved by argparse) |
| **3** | Pre-commit hook drift — use `--pre-commit` flag to enable this check |
| **4** | Upstream unreachable — HTTP error or network failure |

All non-zero codes cause a CI step to fail, which is the desired behaviour. To diagnose which failure occurred, check the exit code with `echo $?` after the `ruff-sync check` call.
