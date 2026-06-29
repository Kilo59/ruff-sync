# Troubleshooting ruff-sync

## Config Not Changing After Sync

**Symptom:** `ruff-sync` runs without error, but `git diff` shows no changes.

**Likely causes:**
1. The key is in `exclude`. Check `[tool.ruff-sync] exclude` in your `pyproject.toml`.
2. The local value already matches upstream — you're already in sync.
3. The upstream URL resolved to the wrong file. Verify with `ruff-sync check --semantic` and look at the diff output.

---

## `UpstreamError` / HTTP Failure

**Symptom:**
```
UpstreamError: Failed to fetch https://...
```

**Steps:**
1. Check the URL works in a browser or with `curl -I <url>`.
2. For GitHub URLs, make sure you're pointing at a _raw_ or _tree/blob_ URL, not an HTML page.
3. If using a private repo, the raw URL requires authentication. Use an SSH URL instead:
   ```bash
   ruff-sync git@github.com:my-org/private-standards.git
   ```
4. Check network/proxy settings if in a corporate environment.

---

## HTTP 404 on GitHub URL

**Symptom:** 404 when fetching a GitHub tree or blob URL.

**Cause:** The branch or path doesn't exist, or the repo is private.

**Fix:**
```toml
[tool.ruff-sync]
upstream = "https://github.com/my-org/standards"
branch = "main"   # make sure this branch exists
path = "configs"  # make sure this path exists on that branch
```

Validate: `curl https://github.com/my-org/standards/tree/main/configs` should return 200.

---

## `FileNotFoundError` — No Local Config

**Symptom:**
```
FileNotFoundError: No pyproject.toml or ruff.toml found in .
```

**Fix:** Use `--init` to scaffold a new config file before syncing:
```bash
ruff-sync https://github.com/my-org/standards --init
```

---

## Pre-commit Version Mismatch (Exit Code 2)

**Symptom:** `ruff-sync check` exits with code 2 and a warning like:
```
⚠️  Pre-commit ruff hook version is out of sync: .pre-commit-config.yaml uses v0.9.3, project has ruff==0.10.0
```

**This is not a config drift.** The Ruff configuration is in sync. Only the pre-commit hook tag is stale.

**Fix:**
```bash
ruff-sync          # pulls config AND updates the hook rev (if pre-commit-version-sync = true)
# or manually: update the 'rev:' line in .pre-commit-config.yaml
```

To suppress this check entirely, omit `--pre-commit` from `ruff-sync check` or set `pre-commit-version-sync = false`.
---

## Python Version Mismatch Warning

**Symptom:** Sync succeeds but logs a warning like:
```
⚠️  Version mismatch: upstream [tool.ruff] target-version='py39' targets Python 3.9, but local [project] requires-python='>=3.10' requires Python >= 3.10.
```

**Cause:** The upstream configuration is targeting an older Python version than your project requires. This can lead to Ruff not using newer rules or features available to your project.

**Fix:**
1. **Update Upstream:** The ideal fix is to update the `target-version` in the upstream repository to a newer version (e.g., `py311`).
2. **Exclude the key:** If you need to stay on a specific version locally, add `target-version` to your `exclude` list:
   ```toml
   [tool.ruff-sync]
   exclude = ["target-version"]
   ```

In **`--strict`** mode, this warning is upgraded to a hard failure and will abort the sync.

---

## Merge Produces Unexpected `tomlkit` Structure

**Symptom:** Synced `pyproject.toml` has repeated sections or oddly formatted keys.

**Cause:** Mixing dotted-key style (`lint.select = [...]`) with explicit table header style (`[tool.ruff.lint]`) in the same file.

**Fix:** Pick one style consistently. `ruff-sync` uses `tomlkit` which preserves formatting, but mixing styles can produce unexpected output.

---

## SSH Clone Fails

**Symptom:** Hangs or fails when using `git@github.com:...` URL.

**Cause:** SSH key not configured or not added to the agent.

**Fix:** Verify SSH auth first:
```bash
ssh -T git@github.com
```

Alternatively, switch to HTTPS:
```toml
upstream = "https://github.com/my-org/standards"
```

---

## `ruff-sync` Not Found After Install

**Symptom:** `ruff-sync: command not found`

**Fix:**
```bash
# If installed with uv tool:
uv tool list   # confirm it appears
# Ensure uv tools bin dir is on PATH:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc

# If using pipx:
pipx ensurepath
```

---

## Getting More Debug Info

```bash
# Show what config would be merged without applying it
ruff-sync check https://github.com/my-org/standards

# Show a diff of what changed
ruff-sync check --semantic   # value-only diff
ruff-sync check              # full string diff (catches comment/whitespace changes too)
```
