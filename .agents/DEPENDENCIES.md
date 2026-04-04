# Optional Dependencies & Lazy Loading

To keep the `ruff-sync` CLI fast and lightweight, while still allowing for extensible features (like a TUI or specialized formatters), we use a standardized pattern for **Optional Dependencies**.

## Requirements

1. **Defensive Coding**: The application must never crash at startup if an optional dependency is missing. Instead, it should fail gracefully ONLY when the specific feature requiring that dependency is invoked.
2. **Delayed Import Cycles**: We must avoid expensive imports of optional dependencies during the initial CLI application boot.
3. **User-Friendly Errors**: If a dependency is missing, we must provide clear instructions on how the user can install it using `ruff-sync` extras.

## Standard Pattern

All code that relies on an optional dependency MUST follow this pattern:

### 1. Define the Extra in `pyproject.toml`

Add the dependency to the `[project.optional-dependencies]` section.

```toml
[project.optional-dependencies]
tui = ["textual>=8.2.2"]
```

### 2. Check and Lazy-Import (Locally)

Never import optional dependencies at the top level of a module. All imports must happen inside the function or method that requires them, AFTER a defensive check.

```python
def run_tui_feature():
    # 1. First, check availability (fast, lightweight)
    from ruff_sync.dependencies import require_dependency
    require_dependency("textual", extra_name="tui")

    # 2. Then, perform local import (delayed expensive cycle)
    from textual.app import App
    ...
```

## The Dependency Helper (`ruff_sync.dependencies`)

Use the utilities in `src/ruff_sync/dependencies.py` to handle these checks.

- `is_installed(package_name: str) -> bool`: A fast check using `importlib.util.find_spec` that doesn't trigger the package initialization.
- `require_dependency(package_name: str, extra_name: str) -> None`: Checks if a package is installed and raises a helpful `ImportError` if it is not.

### Example ImportError
> "The 'textual' package is required for this feature. Install it with: pip install 'ruff-sync[tui]'"
