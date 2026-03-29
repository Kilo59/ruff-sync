![ruff-sync banner](assets/ruff_sync_banner.png)

# ruff-sync

<div class="badges" style="display: flex; gap: 5px; margin-bottom: 20px;">
  <a href="https://pypi.org/project/ruff-sync/"><img src="https://img.shields.io/pypi/v/ruff-sync.svg" alt="PyPI"></a>
  <a href="https://pypi.org/project/ruff-sync/"><img src="https://img.shields.io/pypi/pyversions/ruff-sync.svg" alt="Python Versions"></a>
  <a href="https://github.com/Kilo59/ruff-sync/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Kilo59/ruff-sync.svg" alt="License"></a>
</div>

**ruff-sync** is a lightweight CLI tool to synchronize [Ruff](https://docs.astral.sh/ruff/) linter configuration across multiple Python projects.

## 🚀 Key Features

* **⚡ Fast & Lightweight**: Zero-config needed for most projects.
* **✨ Formatting Preserved**: Keeps all comments and whitespace via `tomlkit`.
* **🛡️ Smart Merging**: Safely merges nested tables without overwriting local overrides.
* **📂 Upstream Layers**: Combine and merge configurations from several sources sequentially.
* **🌐 Flexible Sources**: Automatically resolves GitHub/GitLab browser URLs (repo, tree, or blob) to raw content.
* **📥 Efficient Git Support**: Shallow clones and sparse checkouts for fast extraction.
* **🚀 Zero-Config Bootstrapping**: Use `--init` to scaffold a new project in one command.
* **✅ CI Ready**: Built-in `check` command with semantic comparison logic.
* **🔗 Pre-commit Sync**: Automatically keep your `.pre-commit-config.yaml` Ruff hook version matched with your project's Ruff version.
* **🦾 Agent Skill**: Includes a built-in AI skill to configure and troubleshoot your `ruff-sync` setup.

---

## 🧐 The Problem

Maintaining a consistent Ruff configuration across 10, 50, or 100 repositories is painful. When you decide to adopt a new rule or change a setting, you have to manually update every single `pyproject.toml`.

Internal "base" configurations or shared presets often fall out of sync, or require complex inheritance setups that are hard to debug or don't support modern TOML features.

## 💡 The Solution

`ruff-sync` lets you define a "source of truth" (a URL to a `pyproject.toml` or `ruff.toml`) and pull the `[tool.ruff]` section into your local projects with a single command.

!!! tip "Zero Drift"
    Use `ruff-sync check` in your CI to guarantee that no repository ever drifts from your organization's standards.

---

## 🏁 Quick Start

### 1. Initialize a new project (Optional)

If your local directory doesn't have a configuration file yet, you can fetch a standard and create one instantly using [uvx](https://docs.astral.sh/uv/guides/tools/#running-tools) (which installs and runs `ruff-sync` in one command):

```bash
uvx ruff-sync https://github.com/<my-org>/<standards> --init
```

For more permanent installation options, see the [Installation Guide](installation.md).

### 2. Configure an existing project

Add the upstream URL to your `pyproject.toml` to make it the default:

```toml
[tool.ruff-sync]
upstream = "https://github.com/<my-org>/<standards>/blob/main/pyproject.toml"
```

For more options, see the [Configuration Guide](configuration.md).

### 3. Pull the configuration

Once configured, simply run:

```bash
uvx ruff-sync
```

This will download the upstream file, extract the `[tool.ruff]` section, and merge it into your local file while **preserving your artisanal comments and formatting**.

---

## Learn More

- [Usage Guide](usage.md)
- [URL Resolution & Discovery](url-resolution.md)
- [Configuration Guide](configuration.md)
- [CI Integration](ci-integration.md)
- [Pre-commit Hooks](pre-commit.md)
