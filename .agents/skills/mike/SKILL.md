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
1.  **`dev`**: Represents the current `main` branch. Deployed on every push to `main` when the version string contains `.dev`.
2.  **Stable Releases**: Versioned documentation (e.g., `0.1.4`) created upon release — when the version string does NOT contain `.dev`.
3.  **`stable`**: An alias always pointing to the most recent non-dev release.

## mkdocs.yml Configuration

```yaml
extra:
  version:
    provider: mike

plugins:
  - mike:
      alias_type: redirect   # NOT 'copy' or 'symlink' — redirect is correct for GitHub Pages
      canonical_version: stable
```

### Why `alias_type: redirect`?
- **`symlink`** (default): Creates actual filesystem symlinks. GitHub Pages does not follow symlinks — the alias directory appears empty.
- **`copy`**: Duplicates all files at the alias path. Creates stale copies when the alias moves to a new version.
- **`redirect`**: Creates a thin HTML redirect file for each page at the alias path. Works correctly on GitHub Pages and stays current because it redirects to the canonical versioned path.

## Theme Overrides

To support the version switcher and custom banners, the project uses a `custom_dir` override in `mkdocs.yml`:

```yaml
theme:
  name: material
  custom_dir: docs/overrides
```

### Version switcher

The version switcher is enabled via `extra.version.provider: mike` (shown above).

## Versioning Banner

A custom banner is displayed when users are viewing the `dev` documentation. This is handled via `docs/overrides/main.html` and `docs/overrides/partials/version_warning.html`.

### How it works:
-   `main.html`: Extends the base template and includes the `version_warning.html` partial at the start of the `content` block.
-   `version_warning.html`: Contains an HTML snippet that is hidden by default and shown via JavaScript if the URL path contains `/dev/`.

## CI/CD Integration

> [!CAUTION]
> **Golden Rule**: Only ONE workflow may ever write to `gh-pages`. If two workflows both deploy to `gh-pages`, the second one will overwrite the first, destroying `versions.json` and all versioned directories.
>
> **Never** use `mkdocs gh-deploy` alongside `mike deploy` — they are mutually exclusive deployment strategies. This project uses `mike deploy` exclusively. There is no `docs.yaml` workflow; all deployment happens in `ci.yaml`.

The deployment logic is automated in [.github/workflows/ci.yaml](.github/workflows/ci.yaml). The `publish-docs` job:

1. **Fetches the `gh-pages` branch** before deploying — this is required by mike to make incremental commits. Without it, mike may reset the entire branch.
2. **Detects the version** from `pyproject.toml` using `tomlkit`.
3. **Deploys `dev`** if the version string contains `.dev`.
4. **Deploys a versioned release + `stable` alias** and sets `stable` as the default if not a dev version.

### Key CI snippet

```yaml
- name: Fetch gh-pages branch
  # Required: mike needs the gh-pages branch history for incremental commits.
  run: git fetch origin gh-pages --depth=1 || true

- name: Deploy documentation
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "github-actions[bot]@users.noreply.github.com"

    VERSION=$(uv run python -c "...")

    if [[ "$VERSION" == *".dev"* ]]; then
      uv run mike deploy --push --update-aliases dev
    else
      uv run mike deploy --push --update-aliases "$VERSION" stable
      uv run mike set-default --push stable
    fi
```

## Reference Commands

| Action | Command |
| :--- | :--- |
| **Deploy** | `mike deploy <version> [alias]` |
| **List** | `mike list` |
| **Set Default** | `mike set-default <version>` |
| **Alias** | `mike alias <version> <alias>` |
| **Delete** | `mike delete <identifier>` |
| **Delete all** | `mike delete --all` |

### Deploying Development Docs
Run this from the `main` branch to update the `dev` version:
```bash
mike deploy dev --push --update-aliases
```

### Deploying a Stable Release
When a new version is released (e.g., `0.1.4`), deploy it and update the `stable` alias:
```bash
# Deploy the specific version and update 'stable'
mike deploy 0.1.4 stable --push --update-aliases

# Set 'stable' as the default version for the site root
mike set-default --push stable
```

> [!IMPORTANT]
> **Do NOT** use `mike install-gh-pages`. It is deprecated and removed in the version used by this project. `mike deploy` handles branch initialization automatically.

> [!TIP]
> Use `mike serve` locally to preview the version switcher before pushing changes.

## Troubleshooting

### Version Selector Not Appearing
- **Missing `versions.json`**: Ensure `mike deploy` or `mike update-aliases` has been run. The file must exist at the site root.
- **Incomplete `versions.json`**: If the current page's version (e.g., `stable`) is not listed in `versions.json`, some themes (like Material) may hide the selector.
- **`site_url` Case Sensitivity**: On GitHub Pages, ensure `site_url` in `mkdocs.yml` matches the actual deployment URL (usually lowercase). Discrepancies can cause the switcher to fail to find `versions.json` due to 404s.
- **Redundant Config**: Ensure `theme.version` is NOT set in `mkdocs.yml`. Use `extra.version.provider: mike` instead.
- **`canonical_version` Missing**: If the switcher is hidden on the root page, adding `canonical_version: stable` (or your main alias) to the `mike` plugin configuration can help the theme associate the root with the switcher metadata.

### 404 for `versions.json`
- If you see a 404 for `/versions.json` but `https://<user>.github.io/<repo>/versions.json` exists, the switcher is looking at the domain root instead of the project root. Verify `site_url` includes the repository name and has a trailing slash.

### Corrupted/Stale `gh-pages` Branch
If the `gh-pages` branch was written by `mkdocs gh-deploy` instead of mike, it will be a flat site with no versioning. To reset:

```bash
# WARNING: This deletes all deployed docs. Run locally, then push.
uv run mike delete --all --push
# Then trigger a CI run or deploy manually:
uv run mike deploy --push --update-aliases dev
```
