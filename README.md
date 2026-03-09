<p align="center">
  <img src="https://raw.githubusercontent.com/Kilo59/ruff-sync/main/ruff_sync_banner.png" alt="ruff-sync banner" style="max-width: 600px; width: 100%; height: auto; margin-bottom: 1rem;">
  <br>
  <a href="https://pypi.org/project/ruff-sync/"><img src="https://img.shields.io/pypi/v/ruff-sync" alt="PyPI version"></a>
  <a href="https://codecov.io/gh/Kilo59/ruff-sync"><img src="https://codecov.io/gh/Kilo59/ruff-sync/graph/badge.svg?token=kMZw0XtoFW" alt="codecov"></a>
  <a href="https://results.pre-commit.ci/latest/github/Kilo59/ruff-sync/main"><img src="https://results.pre-commit.ci/badge/github/Kilo59/ruff-sync/main.svg" alt="pre-commit.ci status"></a>
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://wily.readthedocs.io/"><img src="https://img.shields.io/badge/%F0%9F%A6%8A%20wily-passing-brightgreen.svg" alt="Wily"></a>
</p>

# ruff-sync

**Keep your Ruff config consistent across multiple projects.**

`ruff-sync` is a CLI tool that pulls a canonical [Ruff](https://docs.astral.sh/ruff/) configuration from an upstream `pyproject.toml` or `ruff.toml` (hosted anywhere — GitHub, GitLab, or any raw URL) and merges it into your local project, preserving your comments, formatting, and project-specific overrides.

---

### Table of Contents

- [The Problem](#the-problem)
- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Key Features](#key-features)
- [Configuration](#configuration)
- [CI Integration](#ci-integration)
- [Example Workflow](#example-workflow)
- [Detailed Check Logic](#detailed-check-logic)
- [Contributing](#contributing)
- [Dogfooding](#dogfooding)
- [License](#license)

## The Problem

If you maintain more than one Python project, you've probably copy-pasted your `[tool.ruff]` config between repos more than once. When you decide to enable a new rule or bump your target Python version, you get to do it again — in _every_ repo. Configs drift, standards diverge, and your "shared" style guide becomes a polite suggestion.

### How Other Ecosystems Solve This

| Ecosystem | Mechanism | Limitation for Ruff users |
|-----------|-----------|---------------------------|
| **ESLint** | [Shareable configs](https://eslint.org/docs/latest/extend/shareable-configs) — publish an npm package, then `extends: ["my-org-config"]` | Requires a package registry (npm). Python doesn't have an equivalent convention. |
| **Prettier** | [Shared configs](https://prettier.io/docs/sharing-configurations) — same npm-package pattern, referenced via `"prettier": "@my-org/prettier-config"` in `package.json` | Same — tightly coupled to npm. |
| **Ruff** | [`extend`](https://docs.astral.sh/ruff/configuration/#config-file-discovery) — extend from a _local_ file path (great for monorepos) | Only supports local paths. No native remote URL support ([requested in astral-sh/ruff#12352](https://github.com/astral-sh/ruff/issues/12352)). |

Ruff's `extend` is perfect inside a monorepo, but if your projects live in **separate repositories**, there's no built-in way to inherit config from a central source.

**That's what `ruff-sync` does.**

### How It Works

```
┌─────────────────────────────┐
│  Upstream repo              │
│  (your "source of truth")   │
│                             │
│  pyproject.toml             │
│    [tool.ruff]              │
│    target-version = "py310" │
│    lint.select = [...]      │
└──────────┬──────────────────┘
           │  ruff-sync downloads
           │  & extracts [tool.ruff]
           ▼
┌─────────────────────────────┐
│  Your local project         │
│                             │
│  pyproject.toml             │
│    [tool.ruff]  ◄── merged  │
│    # your comments kept ✓   │
│    # formatting kept ✓      │
│    # per-file-ignores kept ✓│
└─────────────────────────────┘
```

1. You point `ruff-sync` at the URL of your canonical `pyproject.toml`.
2. It downloads the file, extracts the `[tool.ruff]` section.
3. It **merges** the upstream config into your local `pyproject.toml` — updating values that changed, adding new rules, but preserving your local comments, whitespace, and any sections you've chosen to exclude (like `per-file-ignores`).

No package registry. No publishing step. Just a URL.

## Quick Start

### Install

With [uv](https://docs.astral.sh/uv/) (recommended):

```console
uv tool install ruff-sync
```

With [pipx](https://pipx.pypa.io/stable/):

```console
pipx install ruff-sync
```

With [pip](https://pip.pypa.io/en/stable/):

```console
pip install ruff-sync
```

#### From Source (Bleeding Edge)

If you want the latest development version:

```console
uv tool install git+https://github.com/Kilo59/ruff-sync
```

### Usage

```console
# Sync from a GitHub/GitLab repository (defaults to main/pyproject.toml)
ruff-sync https://github.com/my-org/standards

# Or a direct blob/file URL (auto-converts to raw)
ruff-sync https://github.com/my-org/standards/blob/main/pyproject.toml

# Clone from any git repository (using SSH or HTTP, defaults to --depth 1)
# You can use the --branch flag to specify a branch (default: main)
ruff-sync git@github.com:my-org/standards.git
ruff-sync ssh://git@gitlab.com/my-org/standards.git

# Or if configured in pyproject.toml (see Configuration), simply run:
ruff-sync

# Exclude specific sections from being overwritten using dotted paths
ruff-sync --exclude lint.per-file-ignores lint.ignore

# Check if your local config is in sync (useful in CI)
ruff-sync check https://github.com/my-org/standards

# Semantic check — ignore cosmetic differences like comments and whitespace
ruff-sync check --semantic
```

Run `ruff-sync --help` for full details on all available options.

## Key Features

- 🏗️ **Format-preserving merges** — Uses [tomlkit](https://github.com/sdispater/tomlkit) under the hood, so your comments, whitespace, and TOML structure are preserved. No reformatting surprises.
- 🌐 **GitHub & GitLab URL support** — Automatically converts GitHub/GitLab repository URLs or blob URLs to raw content URLs.
- 📥 **Git clone support** — If the URL starts with `git@` or uses the `ssh://`, `git://`, or `git+ssh://` schemes, `ruff-sync` will perform an efficient shallow clone (using `--filter=blob:none` and `--no-checkout`) to safely extract the configuration with minimal network traffic.
- 🛡️ **Selective exclusions** — Keep project-specific overrides (like `per-file-ignores` or `target-version`) from being clobbered by the upstream config.
- 🌍 **Works with any host** — GitHub, GitLab, Bitbucket, private SSH servers, or any raw URL that serves a `pyproject.toml` or `ruff.toml`.
- 🤖 **CI-ready `check` command** — Verify that your local config is in sync without modifying anything. Exits 1 if out of sync, making it perfect for pre-merge gates. ([See detailed logic](#detailed-check-logic))
- 🧠 **Semantic mode** — Use `--semantic` to ignore cosmetic differences (comments, whitespace) and only fail on real value changes.

## Configuration

You can configure `ruff-sync` itself in your `pyproject.toml`:

```toml
[tool.ruff-sync]
# The source of truth for your Ruff configuration
upstream = "https://github.com/my-org/standards"

# Use simple names for top-level keys, and dotted paths for nested keys
exclude = [
    "target-version",                      # Top-level [tool.ruff] key — projects target different Python versions
    "lint.per-file-ignores",                # Project-specific file overrides
    "lint.ignore",                         # Project-specific rule suppressions
    "lint.isort.known-first-party",         # Every project has different first-party packages
    "lint.flake8-tidy-imports.banned-api",  # Entire plugin section — project-specific banned APIs
    "lint.pydocstyle.convention",          # Teams may disagree on google vs numpy vs pep257
]
```

This sets the default upstream and exclusions so you don't need to pass them on the command line every time.
*Note: Any explicitly provided CLI arguments will override the values in `pyproject.toml`.*

### Advanced Configuration

Here are all the possible values that can be provided in `[tool.ruff-sync]` along with their explanations and defaults:

```toml
[tool.ruff-sync]
# The source of truth URL for your Ruff configuration. (Required, unless passed via CLI)
upstream = "https://github.com/my-org/standards"

# A list of config keys to exclude from being synced. (Default: ["lint.per-file-ignores"])
# Use simple names for top-level keys, and dotted paths for nested keys.
exclude = [
    "target-version",
    "lint.per-file-ignores",
]

# The branch, tag, or commit hash to use when resolving a Git repository URL. (Default: "main")
branch = "develop"

# A directory prefix to use when looking for a configuration file in a repository. (Default: "")
# Useful if the upstream pyproject.toml is not at the repository root.
path = "config/ruff"
```

## CI Integration

The `check` command is designed for use in CI pipelines. Add it as a step to catch config drift before it merges:

```yaml
# .github/workflows/ci.yaml
- name: Check ruff config is in sync
  run: |
    ruff-sync check --semantic
```

With `--semantic`, minor reformatting of your local file won't cause a false positive — only actual rule or value differences will fail the check.

To see exactly what's drifted, omit `--no-diff` (the default) and the output will include a unified diff:

```console
$ ruff-sync check --semantic
🔍 Checking Ruff sync status...
❌ Ruff configuration at pyproject.toml is out of sync!
--- local (semantic)
+++ upstream (semantic)
@@ -5,6 +5,7 @@
   "select": [
+    "PERF",
     "RUF",
     ...
   ]
```

## Example Workflow

A typical setup for an organization:

1. **Create a "standards" repo** with your canonical `pyproject.toml` containing your shared `[tool.ruff]` config.
2. **In each project**, run `ruff-sync` pointing at that repo — either manually, in a Makefile, or as a CI step.
3. **When you update the standard**, re-run `ruff-sync` in each project to pull the changes. Your local comments and `per-file-ignores` stay intact.

```console
# In each project repo:
ruff-sync https://github.com/my-org/python-standards
git diff pyproject.toml  # review the changes
git commit -am "sync ruff config from upstream"
```

## Bootstrapping a New Project

By default, `ruff-sync` requires an existing configuration file (`pyproject.toml` or `ruff.toml`) to merge into. If you are starting a fresh project and want to initialize it with your organization's Ruff settings, you can use the `--init` flag to scaffold a new file automatically.

```console
# Create a new pyproject.toml (or ruff.toml) pre-configured with upstream settings
ruff-sync pull https://github.com/my-org/standards --init
```

`ruff-sync` seamlessly supports both `pyproject.toml` and standalone `ruff.toml` (or `.ruff.toml`) files. If your upstream source or your local target is a `ruff.toml`, it will automatically adapt and sync the root configuration rather than looking for a `[tool.ruff]` section.


## Detailed Check Logic

When you run `ruff-sync check`, it follows this process to determine if your project has drifted from the upstream source:

```mermaid
flowchart TD
    Start([Start]) --> Local[Read Local pyproject.toml]
    Local --> Upstream[Download Upstream pyproject.toml]
    Upstream --> Extract[Extract tool.ruff section]
    Extract --> Exclude[Apply Exclusions]
    Exclude --> Merge[Perform in-memory Merge]

    subgraph Comparison [Comparison Logic]
        direction TB
        SemanticNode{--semantic?}
        SemanticNode -- Yes --> Unwrap[Unwrap TOML objects to Python Dicts]
        Unwrap --> CompareVal[Compare Key/Value Pairs]
        SemanticNode -- No --> CompareFull[Compare Full File Strings]
    end

    Merge --> Comparison

    CompareVal --> ResultNode{Match?}
    CompareFull --> ResultNode

    ResultNode -- Yes --> Success([Exit 0: In Sync])
    ResultNode -- No --> Diff[Generate Diff]
    Diff --> Fail([Exit 1: Out of Sync])

    %% Styling
    style Start fill:#4a90e2,color:#fff,stroke:#357abd
    style Success fill:#48c774,color:#fff,stroke:#36975a
    style Fail fill:#f14668,color:#fff,stroke:#b2334b
    style ResultNode fill:#ffdd57,color:#4a4a4a,stroke:#d4b106
    style Comparison fill:none,stroke:#9e9e9e,stroke-dasharray: 5 5,stroke-width:2px
    style SemanticNode fill:#f4f4f4,color:#363636,stroke:#dbdbdb
```

## Dogfooding

To see `ruff-sync` in action, you can ["dogfood" it on this project's own config](./scripts).

[**Check if this project is in sync with its upstream:**](./scripts/check_dogfood.sh)

```console
./scripts/check_dogfood.sh
```

[**Or sync from a large upstream like Pydantic's config:**](./scripts/pull_dogfood.sh)

```console
# Using a HTTP URL
./scripts/pull_dogfood.sh
# Using a Git URL
./scripts/gitclone_dogfood.sh
```

This will download Pydantic's Ruff configuration and merge it into the local `pyproject.toml`. You can then use `git diff` to see how it merged the keys while preserving the existing structure and comments.

**To revert the changes after testing:**

```console
git checkout pyproject.toml
```

## License

[MIT](LICENSE.md)
