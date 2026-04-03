---
name: mike
description: Manage multiple versions of MkDocs-powered documentation. Use when deploying, aliasing, or managing versioned documentation sites.
---

# mike: MkDocs Versioning

`mike` is a tool for managing multiple versions of documentation for MkDocs-powered sites. It builds your site and commits the output into a specific Git branch (usually `gh-pages`) in versioned subdirectories.

## Prerequisites

1.  **Install**:
    `mike` is included in the `docs` dependency group in this project.
    ```bash
    # Sync all developer and documentation dependencies
    uv sync --group docs
    ```

    To run `mike` commands:
    ```bash
    uv run mike <command>
    ```

2.  **Configuration**: The `mkdocs.yml` is already configured with `mike` as the versioning provider:
    ```yaml
    extra:
      version:
        provider: mike
    ```

## Core Workflow

### 1. Initial Deployment
Deploy the first version and set it as the default:
```bash
mike deploy 0.1.0 latest --push --update-aliases
mike set-default --push latest
```

### 2. Deploying a New Version
```bash
# Deploy version 0.2.0 and update the 'latest' alias
mike deploy 0.2.0 latest --push --update-aliases
```

### 3. Managing Aliases
Aliases are useful for pointing `latest` or `stable` to a specific version without rebuilding.
```bash
mike alias 0.2.0 stable --push --update-aliases
```

## Reference: Commands

| Action | Command |
| :--- | :--- |
| **Deploy** | `mike deploy <version> [alias]` |
| **List** | `mike list` |
| **Set Default** | `mike set-default <version>` |
| **Alias** | `mike alias <version> <alias>` |
| **Delete** | `mike delete <identifier>` |
| **Delete All** | `mike delete --all` |

## Options

- `--push`, `-p`: Automatically push the new commit to your remote Git repository.
- `--branch`, `-b`: Specify the branch to deploy to (defaults to `gh-pages`).
- `--update-aliases`, `-u`: Required if an alias is already assigned to another version.
- `--alias-type`: `symlink` (default), `redirect` (HTML redirect), or `copy`.

## CI/CD Integration (GitHub Actions)

Example step for deploying versioned docs:

```yaml
- name: Deploy versioned docs
  run: |
    git config --global user.name github-actions
    git config --global user.email github-actions@github.com
    mike deploy --push --update-aliases ${{ github.ref_name }} latest
```

> [!TIP]
> Always run `mike` commands from the specific Git tag or branch corresponding to that version of your software to ensure the documentation matches the code.
