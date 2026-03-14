# ruff-sync

[![PyPI](https://img.shields.io/pypi/v/ruff-sync.svg)](https://pypi.org/project/ruff-sync/)
[![Python Versions](https://img.shields.io/pypi/pyversions/ruff-sync.svg)](https://pypi.org/project/ruff-sync/)
[![License](https://img.shields.io/github/license/Kilo59/ruff-sync.svg)](https://github.com/Kilo59/ruff-sync/blob/main/LICENSE)

**ruff-sync** is a lightweight CLI tool to synchronize [Ruff](https://docs.astral.sh/ruff/) linter configuration across multiple Python projects.

## The Problem

Maintaining a consistent Ruff configuration across 10, 50, or 100 repositories is painful. When you decide to adopt a new rule or change a setting, you have to manually update every single `pyproject.toml`.

Internal "base" configurations or shared presets often fall out of sync, or require complex inheritance setups that are hard to debug.

## The Solution

`ruff-sync` lets you define a "source of truth" (a URL to a `pyproject.toml` or `ruff.toml`) and pull the `[tool.ruff]` section into your local projects with a single command.

- **Formatting Preserved**: Unlike standard TOML parsers, `ruff-sync` uses `tomlkit` to preserve your comments, indentation, and whitespace.
- **Smart Merging**: Intelligently merges nested tables (like `lint.per-file-ignores`) while allowing you to exclude specific keys you want to manage locally.
- **CI Friendly**: Use `ruff-sync check` in your CI pipeline to ensure projects haven't drifted from the upstream standard.

## Quick Start

### 1. Configure your project

Add the upstream URL to your `pyproject.toml`:

```toml
[tool.ruff-sync]
upstream = "https://github.com/my-org/standards/blob/main/pyproject.toml"
```

### 2. Pull the configuration

```bash
uv run ruff-sync pull
```

This will download the upstream file, extract the `[tool.ruff]` section, and merge it into your local file.
