# Specialized Matching for `ruff-sync`

This reference covers project-specific data structures where `dirty-equals` matchers require particular preparation for reliable results.

## TOML Matching (`tomlkit`)

`tomlkit` returns proxy objects (containers and items). To reliably match these with `dirty-equals`, always use `.unwrap()` on the parsed document or table to convert it to plain Python types.

### Correct Pattern

```python
from dirty_equals import IsPartialDict
import tomlkit

# Parse some TOML
doc = tomlkit.parse('[tool.ruff]\nline-length = 80')

# Match the tool.ruff section
ruff_config = doc["tool"]["ruff"]

# Must use .unwrap()
assert ruff_config.unwrap() == IsPartialDict({"line-length": 80})
```

### Potential Gotcha
Direct matching of `tomlkit` proxy objects without `.unwrap()` can fail because `dirty-equals` may see the proxy's internal attributes rather than its data.

## CLI `Arguments` matching

Our CLI arguments are defined as a `NamedTuple`. To match specific fields without validating the entire object, convert it to a dictionary using `._asdict()`.

### Correct Pattern

```python
from dirty_equals import IsInstance, IsPartialDict
import httpx
import pathlib
import ruff_sync_cli

# Sample Arguments instance
args = ruff_sync_cli.Arguments(
    command="pull",
    upstream=(httpx.URL("https://example.com"),),
    to=pathlib.Path("."),
    # ... other defaults ...
)

# Convert to dict and match specific fields
assert args._asdict() == IsPartialDict({
    "command": "pull",
    "upstream": (IsInstance(httpx.URL),),
    "to": IsInstance(pathlib.Path),
})
```
