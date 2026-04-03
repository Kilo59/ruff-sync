---
name: mike
description: Use this skill to manage multiple versions of documentation for MkDocs-powered sites. Deploy new versions, update aliases (like 'latest' or 'stable'), set the default version for the site root, and manage versioned subdirectories in the deployment branch. Use this whenever the user wants to publish, version, or alias documentation, even if they don't explicitly mention "mike". Also use this when the user wants to troubleshoot or debug versioned documentation.
---

# mike: MkDocs Versioning

`mike` is used in this project to manage a versioned documentation site, allowing side-by-side availability of `dev` (main branch) and stable release docs (e.g., `0.1.4`).

## Prerequisites

`mike` is included in the `docs` dependency group.
```bash
# Sync documentation dependencies
uv sync --group docs
```

## Project Strategy

This project follows a specific versioning strategy:
1.  **`dev`**: Represents the current `main` branch.
2.  **Stable Releases**: Versioned documentation (e.g., `0.1.4`) created upon release.
3.  **`stable`**: An alias always pointing to the most recent non-dev release.

## Core Workflows

### 1. Deploying Development Docs
Run this from the `main` branch to update the `dev` version:
```bash
mike deploy dev --push --update-aliases
```

### 2. Deploying a Stable Release
When a new version is released (e.g., `0.1.4`), deploy it and update the `stable` alias:
```bash
# Deploy the specific version and update 'stable'
mike deploy 0.1.4 stable --push --update-aliases

# Set 'stable' as the default version for the site root
mike set-default --push stable
```

## Reference Commands

| Action | Command |
| :--- | :--- |
| **Deploy** | `mike deploy <version> [alias]` |
| **List** | `mike list` |
| **Set Default** | `mike set-default <version>` |
| **Alias** | `mike alias <version> <alias>` |
| **Delete** | `mike delete <identifier>` |

## CI/CD Integration

The deployment logic is automated in [.github/workflows/ci.yaml](.github/workflows/ci.yaml). It automatically:
- Extracts the version from `pyproject.toml`.
- Deploys to `dev` if the version contains `.dev`.
- Deploys to `<version>` and updates `stable` for official releases.

> [!IMPORTANT]
> **Do NOT** use `mike install-gh-pages`. It is deprecated and removed in the version used by this project. `mike deploy` handles branch initialization automatically.

> [!TIP]
> Use `mike serve` locally to preview the version switcher before pushing changes.
