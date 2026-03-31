# Versioned Documentation with `mike`

Add `dev` and stable release doc versions so that pre-release docs are always reachable but never replace the stable docs until an actual release is cut.

## Overview

The tool for this is [`mike`](https://github.com/jimporter/mike) — the standard versioning layer for MkDocs-Material. It manages a `gh-pages` branch where each version lives in its own subdirectory (e.g. `/0.1.3/`, `/dev/`), with a `latest` alias always pointing to the most recent stable release.

### Two published versions

| Version | URL | When deployed |
|---|---|---|
| `dev` | `/dev/` | Every push to `main` |
| `0.x.y` / `latest` | `/latest/` | When a GitHub Release tag is published |

The current site root (`/`) will redirect to `/latest/` automatically.

No version selector version will say something confusing like "0.1.4.dev1" — that becomes `dev`.

---

## Proposed Changes

### `pyproject.toml` — Add `mike` to the `docs` dependency group

#### [MODIFY] [pyproject.toml](file:///Users/gabriel/dev/ruff-sync/pyproject.toml)

Add `mike>=2.1.0` to `[dependency-groups.docs]`.

---

### `mkdocs.yml` — Enable the `mike` version provider

#### [MODIFY] [mkdocs.yml](file:///Users/gabriel/dev/ruff-sync/mkdocs.yml)

Add the `mike` version provider to the `extra:` block and a `version:` key:

```yaml
extra:
  version:
    provider: mike
    default: latest
    alias: true
  social:
    ...
```

This is what enables the version switcher dropdown in the Material theme navbar.

---

### `.github/workflows/docs.yaml` — Replace the flat deploy with versioned deploys

#### [MODIFY] [docs.yaml](file:///Users/gabriel/dev/ruff-sync/.github/workflows/docs.yaml)

Replace the single job with two separate jobs:

**Job 1 — `deploy-dev`**: Triggered on push to `main`. Deploys to the `dev` alias.

```bash
mike deploy --push --update-aliases dev
```

**Job 2 — `deploy-release`**: Triggered on `release: published`. Reads the tag (e.g. `v0.1.3`), strips the `v`, and deploys to both the version number and the `latest` alias. Also sets `latest` as the default redirect.

```bash
VERSION="${GITHUB_REF_NAME#v}"   # strips 'v' from 'v0.1.3'
mike deploy --push --update-aliases "$VERSION" latest
mike set-default --push latest
```

> [!IMPORTANT]
> The `release: published` trigger fires when you publish a release on GitHub (including ones created as drafts). This is exactly the right gate — no stable docs are deployed until you explicitly publish a release.

---

### `tasks.py` — Update the `docs` task to use `mike serve` locally

#### [MODIFY] [tasks.py](file:///Users/gabriel/dev/ruff-sync/tasks.py)

The existing `docs` task uses `mkdocs serve`. Add a `--versioned` flag (or just document) that you can use `mike serve` locally to preview the version switcher. The task itself will continue to call `mkdocs serve` by default (faster for writing), with a note that `mike serve` is available for full version UI testing.

---

## Open Questions

> [!IMPORTANT]
> **The `gh-pages` branch will be restructured.** Currently it holds a flat site. After the first `mike deploy`, it will be reorganized with subdirectories. The first stable deploy (triggered by publishing a release) will set `/latest/` as the default. **Until you publish the first GitHub Release after this change, the `gh-pages` root will redirect to `/latest/` which won't exist yet.** We have two options:
>
> 1. **Bootstrap on merge**: I manually run `mike set-default --push dev` once after the workflow lands, so `/` → `/dev/` temporarily until the first release.
> 2. **Bootstrap on merge + alias**: Deploy `dev` as both `dev` and `latest` initially, then the release workflow will overwrite `latest` when you cut a release.
>
> _Which approach do you prefer? Option 2 is simpler._

> [!NOTE]
> Should the version number in the dropdown show the full semver (e.g. `0.1.3`) or a short form? The standard approach for `mike` is full semver which is fine. Just confirming there's no preference for something like `v0.1.3` (with the `v` prefix).

---

## Verification Plan

### Automated
- The existing `validate-docs-build` CI job (on PRs) continues to run `mkdocs build --strict` — no change needed there.
- After merging: confirm the `deploy-dev` job runs successfully and `/dev/` is live.

### Manual
- After cutting a test release (or using `workflow_dispatch`): verify `/latest/` exists, the version dropdown shows both `dev` and `0.x.y`, and the site root redirects to `/latest/`.
- `mike serve` locally to confirm the dropdown works before the first production deploy.
