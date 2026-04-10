# Configuration

`ruff-sync` can be configured in your `pyproject.toml` file under the `[tool.ruff-sync]` section.

## Reference

| Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `upstream` | `str \| list[str]` | *Required* | The URL(s) of the upstream `pyproject.toml` or `ruff.toml`. |
| `to` | `str` | `"."` | The local directory or file where configuration should be merged. |
| `exclude` | `list[str]` | `["lint.per-file-ignores"]` | A list of configuration keys to preserve locally. |
| `branch` | `str` | `"main"` | The default branch to use when resolving repository URLs. |
| `path` | `str` | `""` | The directory path within the repository where the config is located. |
| `semantic` | `bool` | `false` | Whether `check` should default to semantic matching. |
| `diff` | `bool` | `true` | Whether `check` should show a diff by default. |
| `pre-commit-version-sync` | `bool` | `false` | Sync the pre-commit Ruff hook version with the project's Ruff version. |
| `validate` | `bool` | `false` | Run the merged config through Ruff before writing to disk. Aborts the sync if Ruff rejects the config. |
| `strict` | `bool` | `false` | Treat validation warnings (version mismatches, deprecated rules) as hard failures. Implies `validate = true`. |


## Exclude Patterns

The `exclude` setting is powerful. It allows you to adopt most of an upstream configuration while keeping some parts specific to your repository.

> [!TIP]
> See [Strategic Exclusions](best-practices.md#use-strategic-exclusions) in our Best Practices guide for recommendations on what settings to keep local.

Exclusions use dotted paths to target specific sections or keys.

### Examples

#### Preserve per-file ignores

This is the default. It ensures that any custom ignores you've set for specific files in your repo aren't overwritten by the upstream.

```toml
[tool.ruff-sync]
exclude = ["lint.per-file-ignores"]
```

#### Manage specific plugins locally

If you want to use the upstream rules but manage `pydocstyle` settings yourself:

```toml
[tool.ruff-sync]
exclude = ["lint.pydocstyle"]
```

#### Keep a specific rule toggle

If you want to manage whether a specific rule is ignored or selected:

```toml
[tool.ruff-sync]
exclude = ["lint.ignore", "lint.select"]
```

#### Preserve target version

If your projects are on different Python versions but share linting rules:

```toml
[tool.ruff-sync]
exclude = ["target-version"]
```

> [!NOTE]
> Excluding `target-version` also automatically skips the Python version consistency check otherwise performed during `--validate` or `--strict` runs.

#### Enable validation by default

If you always want the merged config validated before writing, enable it in your configuration:

```toml
[tool.ruff-sync]
validate = true
```

For even stricter enforcement (treat warnings like Python version mismatches and deprecated rules as hard failures):

```toml
[tool.ruff-sync]
strict = true  # implies validate = true
```

#### Sequential merging of multiple sources

You can specify multiple upstream sources as a list. They will be merged in order—from top to bottom—with later sources overriding or extending earlier ones.

```toml
[tool.ruff-sync]
upstream = [
    "https://github.com/my-org/shared-config",  # 1. Base rules
    "https://github.com/my-org/team-overrides", # 2. Team-specific tweaks (wins)
]
```

!!! tip "Last One Wins"
    The merge logic follows a "last one wins" approach for simple keys (like `line-length`), while performing a deep merge for configuration tables like `lint.per-file-ignores`.

## Complete Examples

Here are some complete `pyproject.toml` configuration examples (excluding the core Ruff settings themselves):

### Basic Configuration

Syncs the provided `fastapi` predefined config from the `ruff-sync` repository itself, while keeping your local per-file ignores intact.

```toml
--8<-- "docs/examples/basic-config.toml"
```

### Advanced Configuration

Demonstrates a sequential strategy: it pulls the comprehensive `kitchen-sink` configuration first, then overlays the `fastapi` configuration on top. It also protects your own local `pydocstyle` settings and Python target version from being overwritten, and ensures your pre-commit hooks stay in sync with Ruff's version.

```toml
--8<-- "docs/examples/advanced-config.toml"
```

## Deprecation Notes

- The key `source` in `[tool.ruff-sync]` is deprecated and will be removed in a future version. Use `to` instead.
- The `--source` CLI flag is also deprecated in favor of `--to`.
