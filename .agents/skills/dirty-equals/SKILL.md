---
name: dirty-equals
description: Use for declarative, expressive assertions in Python tests. Ideal for matching complex data structures, TOML documents, and fuzzy matching (URLs, paths, types).
---

## Overview
`dirty-equals` allows you to write assertions that are easier to read and maintain. Instead of asserting on every field manually, compare the entire object against a template.

## Common Matchers
- `IsPositiveInt`: Matches any positive integer.
- `IsStr(regex=...)`: Matches a string against a regex pattern.
- `IsInstance(httpx.URL)`: Matches a valid `httpx.URL` object.
- `IsInstance(pathlib.Path)`: Matches an instance of `pathlib.Path`.
- `IsPartialDict(expected)`: Matches a dictionary containing at least the specified keys.
- `IsList(..., order=False)`: Matches a list of items, optionally ignoring order.

## Project Patterns & Gotchas

### matching `tomlkit` documents
`tomlkit` returns proxy objects. For reliable matching with `dirty-equals`, always call `.unwrap()` on the parsed document or table. We prefer module-level imports for matchers:
```python
from dirty_equals import IsPartialDict
import tomlkit

doc = tomlkit.parse('[tool.ruff]\nline-length = 80')
# Correct: unwrap to a plain dict
assert doc.unwrap() == IsPartialDict({
    "tool": {
        "ruff": {"line-length": 80}
    }
})
```

### matching `Arguments` (NamedTuple)
To match our CLI `Arguments`, convert it to a dictionary first using `._asdict()`:
```python
from dirty_equals import IsInstance, IsPartialDict
import httpx
import pathlib

# Assuming args is a ruff_sync.Arguments instance
assert args._asdict() == IsPartialDict({
    "command": "pull",
    "upstream": (IsInstance(httpx.URL),),
    "to": IsInstance(pathlib.Path),
})
```

### Negative Testing & Logic
- **Negation**: Use `~` (e.g., `assert x == ~IsNone`).
- **Combining**: Use `&` and `|` (e.g., `IsInt & IsPositive`).
