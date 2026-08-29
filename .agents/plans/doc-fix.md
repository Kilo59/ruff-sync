# Fix Versioned Documentation CI (`mike` + MkDocs)

## Summary

After researching the official `mike` README, Material for MkDocs docs, and comparing against real-world projects, the current setup has **one fatal flaw** and several secondary problems that have caused versioning to never work correctly.

---

## Root Cause: Two Workflows Fighting Each Other

The most critical issue is that **two separate workflows both deploy docs to `gh-pages` on every push to `main`**, and they use incompatible methods:

| Workflow | Trigger | Command | Effect |
|---|---|---|---|
| `ci.yaml` → `publish-docs` | push to `main` | `mike deploy --push dev` | Appends a `dev/` directory and `versions.json` to `gh-pages` |
| `docs.yaml` → `deploy` | push to `main` | `mkdocs gh-deploy --force` | **Completely overwrites the entire `gh-pages` branch** |

`mkdocs gh-deploy --force` does not know about `mike`. It builds a flat site and force-pushes it as the **sole content** of `gh-pages`. This destroys everything `mike` deployed, including `versions.json`, the `dev/` subdirectory, and the root redirect.

**This is why versioning has never worked: `docs.yaml` immediately destroys `mike`'s work.**

---

## Secondary Issues

### 1. Wrong `alias_type` in `mkdocs.yml`
- `alias_type: copy` is set, but for GitHub Pages `redirect` is the most reliable option. `copy` creates full file copies for every alias, meaning the `stable` alias contains a complete separate copy of docs that becomes stale when the `stable` alias moves. `symlink` is the default and works on most servers, but GitHub Pages does not follow actual symlinks. `redirect` creates a thin HTML redirect per page at the alias path — the correct approach for GitHub Pages.

### 2. Invalid `mike alias --push stable stable` bootstrap
- The CI attempts `mike alias --push stable stable` to "ensure `stable` exists." This is nonsensical — it tries to create an alias called `stable` pointing to `stable` (which doesn't exist yet). Mike will error, and the `|| true` suppresses it. It achieves nothing.

### 3. `mike deploy --update-aliases dev` on stable releases
- When releasing `0.1.4 stable`, the CI also runs `mike deploy --push --update-aliases dev`. This re-deploys the current commit as *both* the stable `0.1.4` and the `dev` version, which makes `dev` identical to `stable`. `dev` should only be updated on commits to `main` when the version is a dev pre-release.

### 4. The `validate-docs-build` job is fine but could use `--no-directory-urls`
- `mkdocs build --strict` is a good validation step on PRs. No change needed.

---

## Proposed Changes

### [`DELETE`] `.github/workflows/docs.yaml`

This file is the root cause. It must be deleted. All documentation deployment must happen exclusively through `mike` in `ci.yaml`.

---

### [`MODIFY`] `.github/workflows/ci.yaml` — `publish-docs` job

**Fix the deploy logic:**

```yaml
publish-docs:
  name: Publish Documentation
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  needs: [pre-publish]
  runs-on: ubuntu-latest
  permissions:
    contents: write
  steps:
    - name: Checkout
      uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: Fetch gh-pages branch
      # mike needs the gh-pages branch history to make incremental commits.
      # Without this, mike may fail or corrupt the branch.
      run: git fetch origin gh-pages --depth=1 || true

    - name: Install uv
      uses: astral-sh/setup-uv@v5

    - name: Set up Python
      run: uv python install 3.10

    - name: Install dependencies
      run: uv sync --group docs --frozen

    - name: Configure git
      run: |
        git config user.name "github-actions[bot]"
        git config user.email "github-actions[bot]@users.noreply.github.com"

    - name: Extract version
      id: version
      run: |
        VERSION=$(uv run python -c "
        import pathlib, tomlkit
        data = tomlkit.parse(pathlib.Path('pyproject.toml').read_text(encoding='utf-8'))
        version = data.get('project', {}).get('version') or data.get('version')
        if not version: raise SystemExit('Version not found')
        print(version)
        ")
        echo "version=$VERSION" >> $GITHUB_OUTPUT
        echo "Current Version: $VERSION"

    - name: Deploy dev documentation
      if: contains(steps.version.outputs.version, '.dev')
      run: uv run mike deploy --push --update-aliases dev

    - name: Deploy stable documentation
      if: "!contains(steps.version.outputs.version, '.dev')"
      run: |
        VERSION="${{ steps.version.outputs.version }}"
        uv run mike deploy --push --update-aliases "$VERSION" stable
        uv run mike set-default --push stable
```

**Key changes from current:**
1. Added `git fetch origin gh-pages --depth=1 || true` — required by mike to make incremental commits (per the mike README CI section).
2. Split the version extraction into its own step with `id: version` so it can be used in `if` conditions.
3. `dev` is **only** deployed when the version string contains `.dev`. The stable deploy no longer also writes a `dev` alias.
4. Removed the bogus `mike alias --push stable stable || true` bootstrap.

---

### [`MODIFY`] `mkdocs.yml` — Fix `alias_type`

Change `alias_type` from `copy` to `redirect`:

```yaml
plugins:
  - mike:
      alias_type: redirect   # was: copy
      canonical_version: stable
```

`redirect` is the correct choice for GitHub Pages: it creates a lightweight `.html` redirect file at the alias path for every page (e.g., `stable/index.html` redirects to `0.1.4/index.html`). Unlike `symlink`, it works reliably on GitHub Pages. Unlike `copy`, it doesn't create diverging stale copies.

---

### [`MODIFY`] `.agents/skills/mike/SKILL.md`

- Remove the failed repair history section (no longer relevant once fixed)
- Update the CI workflow documentation to reflect the corrected single-workflow approach
- Document the critical `git fetch origin gh-pages --depth=1` requirement
- Document why `docs.yaml` must not exist alongside `mike deploy`
- Update `alias_type` guidance from `copy` to `redirect`

---

## Verification Plan

### After merging:
1. Check that `docs.yaml` is deleted and only `ci.yaml` deploys docs.
2. Watch the next CI run on `main` — the `publish-docs` job should run `mike deploy --push --update-aliases dev`.
3. Check the `gh-pages` branch: it should contain a `dev/` directory, a `versions.json`, and a root `index.html` redirect.
4. Visit `https://kilo59.github.io/ruff-sync/` — it should redirect to `dev/` (since no stable version has been deployed yet).
5. The version selector in the Material theme should appear showing `dev`.

### For stable releases:
When version is bumped to a non-dev release and merged:
- `0.x.y/` directory appears on `gh-pages`
- `stable` alias points to `0.x.y/` via redirects
- Root redirects to `stable/`
- Version selector shows both `0.x.y [stable]` and `dev`

> [!IMPORTANT]
> After deploying, you may need to manually run a one-time `mike deploy --push dev` locally (or trigger the CI) to bootstrap the `gh-pages` branch if it currently contains a flat `mkdocs gh-deploy` dump. You may first want to run `mike delete --all --push` to wipe the broken state.
