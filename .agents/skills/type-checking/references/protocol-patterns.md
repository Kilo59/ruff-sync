# Protocol Patterns (Structural Subtyping)

Use `Protocol` to define interfaces based on structure (capabilities) rather than strict class inheritance. This is essential when working with 3rd-party libraries (like `tomlkit`, `httpx`, `pathlib`) that return complex or internal types.

## Recipe: capability-based Interfaces

Instead of checking `isinstance(obj, pathlib.Path)`, check if it "works like a path."

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class PathLike(Protocol):
    def exists(self) -> bool: ...
    def read_text(self) -> str: ...

def process(path: PathLike) -> str:
    if path.exists():
        return path.read_text()
    return ""
```

## Recipe: Bypassing `Any`

When a library returns `Any`, use a `Protocol` to "tame" it without using `cast`.

```python
from typing import Protocol, Any

class ConfigContainer(Protocol):
    def get(self, key: str) -> Any: ...
    def keys(self) -> list[str]: ...

def load_config(raw: Any) -> ConfigContainer:
    # No cast needed if the argument is structural
    return raw
```

## Recipe: Recursive Protocols

For recursive structures (like nested dicts or file trees), use a `Protocol` that refers to itself.

```python
from typing import Protocol, Union, Optional

class NestedDict(Protocol):
    def __getitem__(self, key: str) -> Union[str, 'NestedDict']: ...
    def get(self, key: str) -> Optional[Union[str, 'NestedDict']]: ...
```

## Best Practices

1. **Keep it Minimal**: Only define the methods you actually need for your function. A `Protocol` with 1 method is better than 10.
2. **Naming**: Prefer `SupportsX` or `Able` suffixes (e.g. `SupportsRead`, `Parsable`).
3. **Internal Protocols**: Mark them with a leading underscore (e.g. `_Mergable`) if they are only used within a single module.
4. **Python 3.10**: Remember that `Protocol` comes from `typing`. No need for `typing_extensions` for the base class.
