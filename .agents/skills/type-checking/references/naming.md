# Naming Conventions for Type-Checking

Maintain consistency in type definitions across the `ruff-sync` project.

## 1. Type Variables (`TypeVar`)

- **Standard T**: Use `T` for a single generic type.
- **Mapping Keys/Values**: Use `KT` (key type) and `VT` (value type) for mapping-related generics.
- **Multiple Generics**: Use `S`, `U`, `V` if more than three are needed.

```python
from typing import TypeVar, Mapping

T = TypeVar("T")
KT = TypeVar("KT")
VT = TypeVar("VT")

def get_keys(data: Mapping[KT, VT]) -> list[KT]:
    return list(data.keys())
```

## 2. Protocols

Follow the standard Python conventions for protocols:
- **`SupportsX`**: Use for capabilities (e.g., `SupportsClose`, `SupportsRead`).
- **`Able` Suffix**: Use for common structural types (e.g., `Closable`, `Mergeable`).

```python
from typing import Protocol

class SupportsMerge(Protocol):
    def merge(self, other: object) -> object: ...
```

## 3. TypedDicts

Use **PascalCase** for `TypedDict` names, as they represent structured objects or configurations.
- Append `Config` if the dict represents a configuration section (e.g., `RuffConfig`, `SyncConfig`).

## 4. Type Aliases

Use **SnakeCase** with an appropriate suffix if the alias is for a complex union or list.
- **Suffixes**: `Type`, `List`, `Map`, `Union`.

```python
from typing import Union

RuffRuleType = Union[str, int, list[str]]
```

## 5. Tomlkit Specifics

Since `tomlkit` returns proxy objects, use descriptive names when narrowing them.
- **`doc`**: For `TOMLDocument`.
- **`tbl`**: For `Table`.
- **`item`**: For generic TOML items.
