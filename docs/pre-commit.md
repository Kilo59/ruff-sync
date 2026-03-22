# Pre-commit Integration

Using `ruff-sync` with [pre-commit](https://pre-commit.com/) ensures that your Ruff configuration stays in sync with your organization's standards automatically.

## Official Hooks

`ruff-sync` provides two official hooks:

### `ruff-sync-check`

Verifies that your local `pyproject.toml` or `ruff.toml` matches the upstream configuration. It is recommended to use this hook to prevent accidental drift.

```yaml
- repo: https://github.com/Kilo59/ruff-sync
  rev: v0.1.0  # Use the latest version
  hooks:
    - id: ruff-sync-check
```

### `ruff-sync-pull`

Automatically pulls and applies the upstream configuration if a drift is detected.

```yaml
- repo: https://github.com/Kilo59/ruff-sync
  rev: v0.1.0  # Use the latest version
  hooks:
    - id: ruff-sync-pull
```

## Configuration

The hooks will automatically respect the configuration defined in your `pyproject.toml` under `[tool.ruff-sync]`. Any arguments passed via `args` in `.pre-commit-config.yaml` will override these settings.

> [!NOTE]
> For a full list of configuration options, see the [Configuration Guide](configuration.md).

### Example `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/Kilo59/ruff-sync
    rev: v0.1.0
    hooks:
      - id: ruff-sync-check
        # Common arguments:
        # --semantic: ignore cosmetic changes (default in check hook)
        # --no-diff: hide the unified diff
        # --to PATH: sync to a specific file or directory
        args: ["--semantic", "--no-diff"]
```

## Why use `ruff-sync-check`?

Running `ruff-sync check` in pre-commit is fast because:

1. It only checks the `[tool.ruff]` section of the configuration.
2. It minimizes network overhead by only fetching exactly what it needs (e.g., using direct HTTP requests for single files or partial git cloning for repositories).
3. By default, it uses `--semantic` to ignore formatting-only differences, reducing false positives.

For more complex scenarios, such as syncing from multiple upstreams or using directory prefixes, see [Usage](usage.md).

## Manual Execution

You can always run the hooks manually using:

```bash
pre-commit run ruff-sync-check --all-files
```

## Syncing the Ruff Hook Version

In addition to syncing your Ruff configuration rules, `ruff-sync` can also automatically synchronize the version of the `astral-sh/ruff-pre-commit` hook in your `.pre-commit-config.yaml` to match the Ruff version installed in your project (e.g., from `uv.lock` or `pyproject.toml`).

To enable this, use the `--pre-commit` flag:

```bash
ruff-sync --pre-commit
```

Or enable it permanently in your `pyproject.toml`:

```toml
[tool.ruff-sync]
pre-commit-version-sync = true
```

If you have `pre-commit-version-sync` enabled in your configuration but need to explicitly disable it for a specific run (for example, during a CI step where pre-commit is turned off), you can bypass it using the `--no-pre-commit` flag:

```bash
ruff-sync check --no-pre-commit
```
