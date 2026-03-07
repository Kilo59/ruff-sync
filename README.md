[![codecov](https://codecov.io/gh/Kilo59/ruff-sync/graph/badge.svg?token=kMZw0XtoFW)](https://codecov.io/gh/Kilo59/ruff-sync)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Kilo59/ruff-sync/main.svg)](https://results.pre-commit.ci/latest/github/Kilo59/ruff-sync/main)
[![Wily](https://img.shields.io/badge/%F0%9F%A6%8A%20wily-passing-brightgreen.svg)](https://wily.readthedocs.io/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PyPI version](https://img.shields.io/pypi/v/ruff-sync)](https://pypi.org/project/ruff-sync/)

# ruff-sync

**Keep your Ruff config consistent across every repo — automatically.**

`ruff-sync` is a CLI tool that pulls a canonical [Ruff](https://docs.astral.sh/ruff/) configuration from an upstream `pyproject.toml` (hosted anywhere — GitHub, GitLab, a raw URL) and merges it into your local project, preserving your comments, formatting, and project-specific overrides.

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

## How It Works

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
# Sync from a GitHub URL (blob URLs are auto-converted to raw)
ruff-sync https://github.com/my-org/standards/blob/main/pyproject.toml

# Sync into a specific project directory
ruff-sync https://github.com/my-org/standards/blob/main/pyproject.toml --source ./my-project

# Exclude specific sections from being overwritten using dotted paths
ruff-sync https://github.com/my-org/standards/blob/main/pyproject.toml --exclude lint.per-file-ignores lint.ignore
```

### CLI Reference

```
usage: ruff-sync [-h] [--source SOURCE] [--exclude EXCLUDE [EXCLUDE ...]] upstream

positional arguments:
  upstream              The URL to download the pyproject.toml file from.

optional arguments:
  -h, --help            show this help message and exit
  --source SOURCE       The directory to sync the pyproject.toml file to. Default: .
  --exclude EXCLUDE [EXCLUDE ...]
                        Exclude certain ruff configs. Default: lint.per-file-ignores
```

## Key Features

- **Format-preserving merges** — Uses [tomlkit](https://github.com/sdispater/tomlkit) under the hood, so your comments, whitespace, and TOML structure are preserved. No reformatting surprises.
- **GitHub URL support** — Paste a GitHub blob URL and it will automatically convert it to the raw content URL.
- **Selective exclusions** — Keep project-specific overrides (like `target-version`) from being clobbered by the upstream config.
- **Works with any host** — GitHub, GitLab, Bitbucket, or any raw URL that serves a `pyproject.toml`.

## Configuration

You can configure `ruff-sync` itself in your `pyproject.toml`:

```toml
[tool.ruff-sync]
# Use simple names for top-level keys, and dotted paths for nested keys
exclude = [
    "target-version",          # A top-level key under [tool.ruff]
    "lint.per-file-ignores",   # A nested key under [tool.ruff.lint]
    "lint.ignore"
]
```

This sets the default exclusions so you don't need to pass `--exclude` on the command line every time.
*Note: Any explicitly provided CLI arguments will override the list in `pyproject.toml`.*

## Example Workflow

A typical setup for an organization:

1. **Create a "standards" repo** with your canonical `pyproject.toml` containing your shared `[tool.ruff]` config.
2. **In each project**, run `ruff-sync` pointing at that repo — either manually, in a Makefile, or as a CI step.
3. **When you update the standard**, re-run `ruff-sync` in each project to pull the changes. Your local comments and `per-file-ignores` stay intact.

```console
# In each project repo:
ruff-sync https://github.com/my-org/python-standards/blob/main/pyproject.toml
git diff pyproject.toml  # review the changes
git commit -am "sync ruff config from upstream"
```

## Contributing

This project uses:

- [uv](https://docs.astral.sh/uv/) for dependency management
- [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- [mypy](https://mypy-lang.org/) for type checking (strict mode)
- [pytest](https://docs.pytest.org/) for testing

```console
# Setup
uv sync --group dev

# Run checks
uv run ruff check . --fix   # lint
uv run ruff format .        # format
uv run mypy .               # type check
uv run pytest -vv           # test
```

## Dogfooding

To see `ruff-sync` in action on a complex, real-world configuration, you can "dogfood" it by syncing this project's own `pyproject.toml` with a large upstream config like Pydantic's.

We've provided a script to make this easy:

```console
./scripts/dogfood.sh
```

This will download Pydantic's Ruff configuration and merge it into the local `pyproject.toml`. You can then use `git diff` to see how it merged the keys while preserving the existing structure and comments.

**To revert the changes after testing:**

```console
git checkout pyproject.toml
```

## License

[MIT](LICENSE.md)
