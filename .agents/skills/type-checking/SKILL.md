---
name: type-checking
description: >-
  Use this skill when Advanced mypy type-checking patterns for Python 3.10 with a
  strict ban on typing.cast. Trigger on keywords like mypy, typing, TypeGuard,
  TypeIs, Protocol, Generic, TypedDict.
---

# Type-Checking Skill

This skill provides advanced patterns and best practices for Python 3.10 type checking, specifically tailored for the `ruff-sync` project's strict environment.

## Quick Start: The "No Cast" Rule

The `ruff-sync` project strictly **bans** `typing.cast` (enforced by Ruff rule `TID251`).
- **Do NOT use `cast()`**. Fix the underlying type issues instead.
- **Last Resort**: If a type issue is truly unsolvable (e.g., due to a library bug), use `# type: ignore[CODE]` but **only after explicitly informing the user** of why it's necessary.

## 1. Advanced Type Narrowing

Since `cast` is banned, use **Type Narrowing** to convince mypy of a specific type.

### TypeGuard vs TypeIs

Use `typing_extensions` for these features in Python 3.10.

| Feature | Branch Narrowing | Best Use Case |
| :--- | :--- | :--- |
| **`TypeGuard[T]`** | Narrows `if` branch to `T`. | General boolean checks. |
| **`TypeIs[T]`** | Narrows `if` to `T` AND `else` to "not `T`". | Partitioning a union (e.g., `str | int`). |

```python
from typing_extensions import TypeGuard, TypeIs

# Use TypeIs when the check definitively partitions the type
def is_str(val: object) -> TypeIs[str]:
    return isinstance(val, str)

def process(val: str | int):
    if is_str(val):
        reveal_type(val)  # str
    else:
        reveal_type(val)  # int
```

## 2. Structural Subtyping (Protocols)

Use `Protocol` to define interfaces based on behavior (duck typing) rather than inheritance.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Closable(Protocol):
    def close(self) -> None: ...

def close_all(items: list[Closable]):
    for item in items:
        item.close()
```
- Use `@runtime_checkable` if you need to use `isinstance(obj, Closable)` at runtime.

## 3. Generics in Python 3.10

Since PEP 695 (the `[T]` syntax) is not available in 3.10, use `TypeVar` and `Generic`.

```python
from typing import TypeVar, Generic, Iterable

T = TypeVar("T")

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)
```

## 4. TypedDict & TOML Handling

The `ruff-sync` project uses `tomlkit`, which returns complex proxy objects. Use `TypedDict` to bridge the gap between raw TOML and structured data.

```python
from typing import TypedDict
from typing_extensions import ReadOnly

class Config(TypedDict, total=False):
    upstream: ReadOnly[str | list[str]]
    to: str
    exclude: list[str]
```
- Use `ReadOnly` (from `typing_extensions`) for fields that shouldn't be mutated.
- Use `total=False` for configurations where most keys are optional.

## 5. Tomlkit "Gotchas"

`tomlkit` proxy objects (like `Table`, `Item`) often lose specific type information.
- Use `.unwrap()` to get a plain Python object (dict, list, etc.) when you don't need to preserve TOML formatting.
- When indexing a `TOMLDocument` in tests, you may use `cast(Any, doc["tool"])["ruff"]` because the project allows `cast(Any, ...)` **only in tests** to simplify `tomlkit` interactions.

## Verification

Always verify your changes by running:
```bash
uv run mypy
```
This command will check the entire project (as configured in `pyproject.toml`).

## References

- [Naming Conventions](references/naming.md) — How to name types and protocols.
- [Mypy Docs: Type Narrowing](https://mypy.readthedocs.io/en/stable/type_narrowing.html)
- [Mypy Docs: Protocols](https://mypy.readthedocs.io/en/stable/protocols.html)
