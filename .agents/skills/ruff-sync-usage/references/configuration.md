# ruff-sync Configuration Reference

All keys live under `[tool.ruff-sync]` in `pyproject.toml`.

## Keys

### `upstream` *(required unless passed on CLI)*

The URL(s) of your canonical Ruff configuration. Accepts a single string or a list. When a list is given, sources are merged in order — later entries win on conflict.

```toml
# Single source
upstream = "https://github.com/my-org/standards"

# Multiple sources (base + team overlay)
upstream = [
    "https://github.com/my-org/python-standards",
    "https://github.com/my-org/ml-team-tweaks",
]
```

**Supported URL formats (with automatic browser link resolution):**
- GitHub/GitLab repo root: `https://github.com/<org>/<repo>`
- Subdirectory (tree): `https://github.com/<org>/<repo>/tree/main/configs/ruff`
- Specific file (blob): `https://github.com/<org>/<repo>/blob/main/pyproject.toml`
- Raw URL: `https://raw.githubusercontent.com/<org>/<repo>/main/pyproject.toml`
- SSH (triggers shallow clone): `git@github.com:<org>/<repo>.git`

---

### `exclude` *(default: `["lint.per-file-ignores"]`)*

List of config keys to protect from being overwritten by upstream. Use dotted paths to reference nested keys.

```toml
exclude = [
    "target-version",                       # keep per-project Python version
    "lint.per-file-ignores",               # keep per-file suppressions
    "lint.ignore",                          # keep repo-specific rule suppressions
    "lint.isort.known-first-party",         # keep first-party package list
    "lint.flake8-tidy-imports.banned-api",  # keep banned API list
    "lint.pydocstyle.convention",           # keep docstring style choice
]
```

**Key format:**
- Top-level keys: `"target-version"`, `"line-length"`
- Nested keys (dotted): `"lint.select"`, `"lint.per-file-ignores"`, `"format.quote-style"`
- These are ruff config key names, NOT TOML paths — do NOT include `tool.ruff.` prefix.

---

### `branch` *(default: `"main"`)*

The branch, tag, or commit hash to use when fetching from a Git repo URL.

```toml
branch = "develop"
```

---

### `path` *(default: `""`)*

Path inside the repository where the config lives, when it's not at the repo root.

```toml
path = "configs/ruff"
```

Useful when combined with a repo-root `upstream` URL:

```toml
upstream = "git@github.com:my-org/standards.git"
path = "configs/strict"
```

---

### `to` *(default: `"."`)*

Local target directory or file path to sync into.

```toml
to = "services/api"   # sync into a subdirectory of the monorepo
```

---

### `pre-commit-version-sync` *(default: `false`)*

When `true`, `ruff-sync` also updates the `ruff-pre-commit` hook rev in `.pre-commit-config.yaml` to match the Ruff version installed in the project.

> [!TIP]
> This is the preferred way to enable pre-commit hook synchronization as it persists the setting in your project configuration.

```toml
pre-commit-version-sync = true
```

Requires a `- repo: https://github.com/astral-sh/ruff-pre-commit` entry in `.pre-commit-config.yaml`.

---

## Full Example

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
```

## CLI Overrides

All config keys have CLI equivalents. CLI values always win over `pyproject.toml`:

```bash
ruff-sync https://github.com/my-org/standards --exclude lint.ignore --branch develop --output-format github
```

## Config Discovery for `ruff.toml` Projects

If the local target is a directory, ruff-sync looks for config in this order:
1. `ruff.toml`
2. `.ruff.toml`
3. `pyproject.toml`

If the upstream is a `ruff.toml`, it syncs the root config object (no `[tool.ruff]` section extraction needed).
