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
4.  **`latest`**: An alias pointing to the most recent release (including dev, if applicable).

## Theme Overrides

To support the version switcher and custom banners, the project uses a `custom_dir` override in `mkdocs.yml`:

```yaml
theme:
  name: material
  custom_dir: docs/overrides
```

### Version switcher

The version switcher is enabled via `extra.version.provider: mike`:

```yaml
extra:
  version:
    provider: mike
```

## Versioning Banner

A custom banner is displayed when users are viewing the `dev` documentation. This is handled via `docs/overrides/main.html` and `docs/overrides/partials/version_warning.html`.

### How it works:
-   `main.html`: Extends the base template and includes the `version_warning.html` partial at the start of the `content` block.
-   `version_warning.html`: Contains an HTML snippet that is hidden by default and shown via JavaScript if the URL path contains `/dev/`.

Example in `version_warning.html`:
```html
<div id="version-warning" style="display: none;">
  <div class="admonition warning">
    <p class="admonition-title">Warning</p>
    <p>
      You are viewing the documentation for the <strong>development</strong> version.
      The latest stable release can be found at <a href="https://kilo59.github.io/ruff-sync/">kilo59.github.io/ruff-sync</a>.
    </p>
  </div>
</div>
<script>
  (function() {
    const version_warning = document.getElementById("version-warning");
    if (!version_warning) return;

    // mike provides a 'mike' object with some metadata if available
    // Otherwise fall back to checking the pathname
    const isDev = window.location.pathname.includes("/dev/") ||
                 (window.mike && typeof window.mike.version === 'string' && window.mike.version === "dev");

    if (isDev) {
      version_warning.style.display = "block";
    }
  })();
</script>
```

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

## Troubleshooting

### Version Selector Not Appearing
- **Missing `versions.json`**: Ensure `mike deploy` or `mike update-aliases` has been run. The file must exist at the site root.
- **Incomplete `versions.json`**: If the current page's version (e.g., `stable`) is not listed in `versions.json`, some themes (like Material) may hide the selector.
- **`site_url` Case Sensitivity**: On GitHub Pages, ensure `site_url` in `mkdocs.yml` matches the actual deployment URL (usually lowercase). Discrepancies can cause the switcher to fail to find `versions.json` due to 404s.
- **Redundant Config**: Ensure `theme.version` is NOT set in `mkdocs.yml`. Use `extra.version.provider: mike` instead.
- **`canonical_version` Missing**: If the switcher is hidden on the root page, adding `canonical_version: stable` (or your main alias) to the `mike` plugin configuration can help the theme associate the root with the switcher metadata.

### 404 for `versions.json`
- If you see a 404 for `/versions.json` but `https://<user>.github.io/<repo>/versions.json` exists, the switcher is looking at the domain root instead of the project root. Verify `site_url` includes the repository name and has a trailing slash.

## Post-Mortem & Known Issues

> [!CAUTION]
> **Current Status**: Documentation versioning is currently **BROKEN** on the live site (`kilo59.github.io/ruff-sync`).

### Failed Repair History
The following fixes have been attempted and **FAILED** to resolve the issue:
1.  **Lowercasing `site_url`**: Normalizing the repository name in the URL (e.g., `ruff-sync` instead of `Ruff-Sync`) did not fix the 404s for `versions.json`.
2.  **Removing `theme.version`**: Removing the redundant Material 9.x config did not restore the switcher.
3.  **Adding `canonical_version: stable`**: Adding this to the `mike` plugin in `mkdocs.yml` was intended to fix path resolution but has not fixed the root page 404.
4.  **CI Restoration Logic**: Adding `mike alias --push stable stable` to the CI to manually repair `versions.json` hasn't restored the picker on the root page.

### Root Cause Suspicions
- **GitHub Pages Subfolder Pathing**: The site is served from a subfolder (`/ruff-sync/`). `mike`'s JavaScript for the version switcher frequently struggles with calculating relative paths to `versions.json` when served from a subfolder if `site_url` or base paths are not perfectly aligned with the deployment environment.
- **`versions.json` Drift**: The `versions.json` file on the `gh-pages` branch frequently becomes desynchronized or loses the `stable` entry, which triggers `mkdocs-material` to hide the switcher entirely.

### Guidance for Future Agents
Before attempting another "fix," you **MUST** verify the current state of `versions.json` on the `gh-pages` branch and check the browser console on the live site for 404 paths. Do not assume standard configurations will work without manual verification of the deployed assets.
