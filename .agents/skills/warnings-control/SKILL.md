---
name: warnings-control
description: >-
  Handle python warnings properly by emitting them with warnings.warn, catching
  them in tests with catch_warnings, and translating them to errors if running
  in strict mode or via filterwarnings.
---

# Python Warnings Control

Use this skill when you need to raise a warning to the user (instead of logging or raising an exception), when testing code that emits warnings, or when implementing `--strict` modes where warnings should become errors.

## Understanding Custom Warning Classes

When working on a library or a CLI tool, you should almost always define a custom base warning class (and potentially subclasses) instead of emitting a bare `UserWarning`.

**Why?**
1. **Targeted Filtering**: If a user runs your tool in `--strict` mode to catch configuration mistakes, you only want to turn *your project's* warnings into errors. If you use a global `warnings.simplefilter('error')`, any minor `DeprecationWarning` from a third-party dependency (like `httpx` or `tomlkit`) will crash your application.
2. **User Experience**: Users can easily choose to ignore *only* your project's warnings if they want to.

```python
# src/my_project/exceptions.py
class ProjectWarning(UserWarning):
    """Base category for warnings related to this project."""
    pass

class ConfigWarning(ProjectWarning):
    """Category for configuration-related warnings."""
    pass
```

## Quick Start: Emitting Warnings

To emit a warning to the user, use `warnings.warn` targeting your custom class:

```python
import warnings
from my_project.exceptions import ConfigWarning

# ALWAYS use stacklevel=2 so the warning points to the user's calling code
# (e.g. the CLI command execution) rather than the internal warning-emitting utility.
warnings.warn(
    "Some configuration option is obsolete.",
    category=ConfigWarning,
    stacklevel=2,
)
```

## Quick Start: Promoting Project Warnings to Errors (Strict Mode)

When implementing a `--strict` mode, use `warnings.filterwarnings` to target *only* your custom base class, rather than `warnings.simplefilter`.

```python
import warnings
from my_project.exceptions import ProjectWarning

def enable_strict_mode():
    """Convert only this project's warnings into exceptions."""
    # This ensures third-party dependency warnings are left alone,
    # but our project's warnings are raised as hard failures.
    warnings.filterwarnings("error", category=ProjectWarning)
```

### A Warning on `PYTHONWARNINGS`

**Do NOT use `PYTHONWARNINGS` to filter custom project warning classes.**

Since Python parses `PYTHONWARNINGS` flags before user code is imported, trying to set `PYTHONWARNINGS="error::my_project.exceptions.ProjectWarning"` will fail with `Invalid -W option ignored: unknown warning category`.

Additionally, the `module` field in `PYTHONWARNINGS` matches **exact literal module paths only** (not regex). `error:::my_project` will not match warnings emitted from `my_project.core`.

If you need to enforce strict warnings in a subprocess, use an application-specific environment variable that configures `warnings.filterwarnings` directly in the child process's initialization:

```python
import os
import subprocess

env = os.environ.copy()
env["MY_PROJECT_STRICT"] = "1"
# In your cli.py: if os.environ.get("MY_PROJECT_STRICT"): warnings.filterwarnings("error", category=ProjectWarning)
subprocess.run(["sys_command"], env=env)
```

## Quick Start: Testing Warnings

When testing code that raises warnings, wrap the operation in `warnings.catch_warnings(record=True)`.

```python
import warnings

def test_deprecated_feature():
    with warnings.catch_warnings(record=True) as w:
        # Guarantee all warnings are captured instead of being filtered
        warnings.simplefilter("always")

        # Trigger the warning
        my_function_that_warns()

        assert len(w) == 1
        assert issubclass(w[-1].category, UserWarning)
        assert "deprecated" in str(w[-1].message)
```

## Gotchas & Rules

- **Do NOT raise standard exceptions (like `ValueError` or `RuntimeError`) for non-fatal issues.** If the user's config is slightly odd but still functionally valid, use `warnings.warn()`.
- **Always use `stacklevel=2`** or higher so the printed warning references the caller's code rather than internal library logic.
- **Do NOT globally suppress warnings** (e.g., `warnings.simplefilter("ignore")`) in library functions, because users may be relying on them.
