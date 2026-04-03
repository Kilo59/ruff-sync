---
name: dirty-equals
description: Use this skill when you need to write declarative, readable, and maintainable assertions in Python tests. It is particularly effective for matching complex data structures, validating merged TOML configurations, and performing fuzzy matching on URLs, file paths, or object types. Use this when the user asks to "assert," "check," "verify," or "match" data in a test, even if they don't explicitly mention "dirty-equals."
---

# `dirty-equals` Skill

This skill provides patterns and best practices for writing declarative assertions in the `ruff-sync` project using the `dirty-equals` library.

## Overview

Instead of asserting on every field manually, compare against a "dirty" object that matches the expected structure and types.

```python
from dirty_equals import IsInt, IsPartialDict, IsStr

def test_config_logic():
    result = {"status": "active", "version": 1, "extra": "data"}
    # Declarative assertion
    assert result == IsPartialDict({
        "status": IsStr(regex="act.*"),
        "version": IsInt(gt=0),
    })
```

## Detailed reference

Check these references for project-specific usage and common matchers:

- **[Common Matchers](references/common-matchers.md)**: Standard `dirty-equals` matchers like `IsPartialDict`, `IsInstance`, and more.
- **[Specialized Matching](references/toml-matching.md)**: Handling `tomlkit.unwrap()` and `Arguments._asdict()`.

## Best Practices

- **Import Style**: Always use the `from dirty_equals import ...` style at the **module level** of your test files.
- **Semantic Matching**: Use `dirty-equals` for the semantic part of your test assertions, while using string comparisons or `respx` for structural/whitespace checks where appropriate.
- **Type Safety**: Prefer `IsInstance(httpx.URL)` or `IsInstance(pathlib.Path)` over custom regex for well-known types in the project.
