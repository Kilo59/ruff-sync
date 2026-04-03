# Common `dirty-equals` Matchers

This guide covers the most frequently used `dirty-equals` matchers in the `ruff-sync` project. Standard practice is to import these using the `from` syntax at the module level in test files.

## Structural Matching

- **`IsPartialDict`**: Matches a subset of a dictionary. Essential for verifying specific fields in a larger configuration.
- **`IsDict`**: Matches an entire dictionary exactly (while still allowing fuzzy values).
- **`IsList`**: Matches a list, allowing fuzzy matching for elements.

## Type and Instance Matching

- **`IsInstance(type)`**: Matches an object of a specific class. Used for objects like `httpx.URL` or `pathlib.Path`.
- **`IsStr()`**: Matches any string. Can also specify regex or prefix/suffix.
- **`IsInt()`**: Matches any integer.

## Examples

### Using `IsPartialDict` and `IsInstance`

```python
from dirty_equals import IsInstance, IsPartialDict
import httpx
import pathlib

# Match a partial dict with mixed types
assert response_data == IsPartialDict({
    "url": IsInstance(httpx.URL),
    "status": "success",
    "retries": 0,
})
```

### String and Path Matching

```python
from dirty_equals import IsInstance, IsStr
import pathlib

# Match a path instance
assert result_path == IsInstance(pathlib.Path)

# Match a string with a specific prefix
assert error_message == IsStr(regex="^ERROR:.*")
```

## Logic Matchers

- **`~` (Negation)**: Match values that are *not* the given value (e.g., `assert x == ~IsNone`).
- **`&` (AND)**: Combine matchers (e.g., `IsInt & IsPositive`).
- **`|` (OR)**: Combine alternatives.
