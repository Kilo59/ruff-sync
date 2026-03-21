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

If you want to use the upstream rules but manage `isort` settings yourself:

```toml
[tool.ruff-sync]
exclude = ["lint.isort"]
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

## Deprecation Notes

- The key `source` in `[tool.ruff-sync]` is deprecated and will be removed in a future version. Use `to` instead.
- The `--source` CLI flag is also deprecated in favor of `--to`.
