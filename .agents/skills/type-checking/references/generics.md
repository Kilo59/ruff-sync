# Advanced Generics (Variance and Bound Variables)

In Python 3.10, variance (covariance, contravariance) is handled via `TypeVar` arguments.

## Why Variance Matters?

Variance determines if a `List[Dog]` is compatible with a `List[Animal]`.

| Variance | Rule | TypeVar Syntax | Example Interface |
| :--- | :--- | :--- | :--- |
| **Invariant** | Same type only. | `T = TypeVar("T")` | `MutableSequence[T]` |
| **Covariant** | Subtypes allowed (`Dog` -> `Animal`). | `T = TypeVar("T", covariant=True)` | `Sequence[T]` (Read-only) |
| **Contravariant** | Supertypes allowed. | `T = TypeVar("T", contravariant=True)` | `Callable[[T], None]` (Write-only) |

### Recipe: Defining a Covariant Interface

Always use `covariant=True` for read-only interfaces or return types.

```python
from typing import TypeVar, Protocol, Generic, Sequence

T = TypeVar("T_co", covariant=True)

class Producer(Generic[T]):
    def __init__(self, items: Sequence[T]) -> None:
        self._items = items

    def produce(self) -> T:
        return self._items[0]
```

## Recipe: Bound Type Variables

Use `bound` to restrict a `TypeVar` to a specific class hierarchy.

```python
from typing import TypeVar, Union

# T must be a subclass of int (including int itself)
T = TypeVar("T", bound=int)

def increment(val: T) -> T:
    return val + 1 # Error: + 1 returns int, but we must return T
```
- **Pro Tip**: Use a `Protocol` as a bound to restrict a `TypeVar` to objects with specific methods.

```python
from typing import Protocol, TypeVar

class SupportsRead(Protocol):
    def read(self) -> str: ...

T = TypeVar("T", bound=SupportsRead)
```

## Best Practices

1. **Avoid `Any` Generics**: Use `disallow_any_generics = true` (already set in `pyproject.toml`) and ALWAYS provide a `TypeVar` or concrete type.
2. **Implicit Variance**: Remember that `list`, `set`, and `dict` are **invariant**. If you need covariance, use `Sequence`, `Set` (frozenset), or `Mapping`.
3. **Naming**: Use `T_co` for covariant and `T_contra` for contravariant type variables to improve readability.
