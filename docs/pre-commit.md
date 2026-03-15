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

The hooks will respect the configuration defined in your `pyproject.toml` under `[tool.ruff-sync]`.

### Example `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/Kilo59/ruff-sync
    rev: v0.1.0
    hooks:
      - id: ruff-sync-check
        # You can override the default --semantic flag if you want strict checking
        # args: []
```

## Why use `ruff-sync-check`?

Running `ruff-sync check` in pre-commit is fast because:

1. It only checks the `[tool.ruff]` section.
2. It uses caching (if configured via HTTP headers).
3. By default, it uses `--semantic` to ignore formatting-only differences, reducing false positives.

## Manual Execution

You can always run the hooks manually using:

```bash
pre-commit run ruff-sync-check --all-files
```
