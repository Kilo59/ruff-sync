# Troubleshooting

Common issues and questions when using `ruff-sync`.

## Common Issues

### Debug Logging

If `ruff-sync` is not behaving as expected, you can increase the verbosity of the logs to see what's happening under the hood.

**Usage**:

- `-v`: Shows `INFO` level logs (e.g., which configuration file is being used, where upstreams are being sourced from).
- `-vv`: Shows `DEBUG` level logs (e.g., detailed TOML merging operations and raw HTTP/Git requests).

Example:

```bash
ruff-sync -vv
```

### Upstream URL not found

**Error**: `Error: Upstream Required. No upstream URL found in pyproject.toml or provided as argument.`

**Solution**:

1. Ensure you have a `[tool.ruff-sync]` section in your `pyproject.toml` with an `upstream` key. See the [Configuration](configuration.md) guide for details.
2. Or provide the URL directly as an argument: `ruff-sync https://github.com/org/repo/blob/main/pyproject.toml`

### Local file not found (with `check`)

**Error**: `FileNotFoundError: pyproject.toml not found`

**Solution**:
The `check` command expects a local `pyproject.toml`, `ruff.toml`, or `.ruff.toml` to exist. If you are setting up a new project, use `ruff-sync --init` first.

### Merge conflicts in TOML

`ruff-sync` uses `tomlkit` to perform a smart merge. It generally doesn't produce "conflicts" in the traditional sense, but if you have a key locally that is ALSO in the upstream, the upstream will generally win UNLESS you exclude it.

**Solution**:
Use the `--exclude` flag to keep your local settings:

```bash
ruff-sync --exclude lint.line-length
```

### Validation failed: `ruff` not found

**Warning**: `⚠️  \`ruff\` not found on PATH — skipping Ruff config validation.`

**Solution**: This is a soft warning, not a failure. If you explicitly want validation, ensure `ruff` is installed and available on your PATH. If using `uv`, run `uv pip install ruff` or add it to your project's dependencies.

### Python version mismatch

**Warning**: `⚠️  Version mismatch: upstream [tool.ruff] target-version='py39'...`

**Solution**:
This means the upstream configuration targets a different Python version than your project's `requires-python`. You have three options:

1. **Update upstream**: Coordinate with your team to update the upstream `target-version`.
2. **Exclude the key**: Add `target-version` to your `exclude` list to manage it locally.
3. **Ignore the warning**: In non-strict mode, this is informational only and does not block the sync.

In `--strict` mode, this warning becomes a hard failure. See the [Usage Guide](usage.md#validating-before-writing) for details.

### Deprecated rule detected

**Warning**: `⚠️  Upstream config uses deprecated rule 'XXX'...`

**Solution**:
The upstream configuration references a Ruff rule that has been deprecated. This often happens when the upstream hasn't been updated after a Ruff version bump.

1. **Update upstream**: Replace the deprecated rule with its successor in the upstream config.
2. **Ignore the warning**: In non-strict mode, deprecated rules are informational warnings only.

In `--strict` mode, deprecated rules cause a hard failure.

### Multi-upstream Fetch Failures

**Error**: `❌ <N> upstream fetches failed`

This happens when one or more of the specified upstream URLs cannot be reached, do not exist, or return an error (e.g., 404 or 403). `ruff-sync` fetches all upstreams concurrently for speed, but requires ALL of them to succeed before it will attempt to merge.

**Solution**:
1. Check each URL in the terminal output to see which specific one failed.
2. Verify you have network access and the correct permissions for each source.
3. If an HTTP source is blocked or private, consider using a Git SSH URL instead.

### Git SSH Workaround for Fetch Errors

If you see an HTTP `403 Forbidden` or `404 Not Found` when trying to fetch from GitHub or GitLab, it might be due to authentication requirements.

**Solution**:
Use the git-clone alternative suggested in the error message:

```bash
ruff-sync git@github.com:org/repo.git
```

This uses your local SSH keys and is often more reliable for internal or private repositories.

## FAQ

### Does it support `ruff.toml`?

Yes, `ruff-sync` automatically detects and supports `pyproject.toml`, `ruff.toml`, and `.ruff.toml`.

### Can I sync from a private repository?

Yes, if you use a Git SSH URL (e.g., `git@github.com:org/repo.git`), `ruff-sync` will use your local SSH credentials to clone and extract the configuration.

### How do I automate this in CI?

See the [CI Integration](ci-integration.md) guide for GitHub Actions and GitLab CI examples.

### Does `--validate` require `ruff` to be installed?

Yes, validation shells out to the `ruff` binary. If `ruff` is not on your `PATH`, validation is silently skipped with a warning. To use validation, ensure Ruff is installed (e.g., via `uv pip install ruff` or as a project dependency).

### What does `--strict` check for?

In addition to the basic config syntax validation from `--validate`, `--strict` upgrades the following warnings to hard failures:

1. **Python version mismatch**: The upstream `target-version` doesn't align with your local `requires-python`.
2. **Deprecated Ruff rules**: Any rule codes in `lint.select`, `lint.ignore`, `lint.extend-select`, `lint.extend-ignore`, or `lint.extend-fixable` that Ruff reports as deprecated.
3. **Ruff stderr warnings**: Any warning messages Ruff emits to stderr when parsing the config.
