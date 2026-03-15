# Troubleshooting

Common issues and questions when using `ruff-sync`.

## Common Issues

### Upstream URL not found

**Error**: `Error: Upstream Required. No upstream URL found in pyproject.toml or provided as argument.`

**Solution**:

1. Ensure you have a `[tool.ruff-sync]` section in your `pyproject.toml` with an `upstream` key. See the [Configuration](configuration.md) guide for details.
2. Or provide the URL directly as an argument: `ruff-sync pull https://github.com/org/repo/blob/main/pyproject.toml`

### Local file not found (with `check`)

**Error**: `FileNotFoundError: pyproject.toml not found`

**Solution**:
The `check` command expects a local `pyproject.toml` or `ruff.toml` to exist. If you are setting up a new project, use `pull --init` first.

### Merge conflicts in TOML

`ruff-sync` uses `tomlkit` to perform a smart merge. It generally doesn't produce "conflicts" in the traditional sense, but if you have a key locally that is ALSO in the upstream, the upstream will generally win UNLESS you exclude it.

**Solution**:
Use the `--exclude` flag to keep your local settings:

```bash
ruff-sync pull --exclude lint.line-length
```

## FAQ

### Does it support `ruff.toml`?

Yes, `ruff-sync` automatically detects and supports both `pyproject.toml` and `ruff.toml`.

### Can I sync from a private repository?

Yes, if you use a Git SSH URL (e.g., `git@github.com:org/repo.git`), `ruff-sync` will use your local SSH credentials to clone and extract the configuration.

### How do I automate this in CI?

See the [CI Integration](ci-integration.md) guide for GitHub Actions and GitLab CI examples.
