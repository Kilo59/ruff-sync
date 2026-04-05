# Advanced Narrowing (TypeIs vs TypeGuard)

In Python 3.10, use `typing_extensions` to access `TypeIs` (PEP 742) and `TypeGuard` (PEP 647).

## Why `TypeIs`?

`TypeIs` is more powerful than `TypeGuard` because it narrows **both** branches of an `if` statement.

| Feature | `TypeGuard[T]` | `TypeIs[T]` |
| :--- | :--- | :--- |
| **If branch** | Narrow to `T` | Narrow to `T` |
| **Else branch** | No change | **Narrow to "Not T"** |

### Recipe: Partitioning a Union

Use `TypeIs` when you want to definitively split a Union.

```python
from typing import Union
from typing_extensions import TypeIs

def is_str(val: Union[str, int]) -> TypeIs[str]:
    return isinstance(val, str)

def process(val: Union[str, int]) -> None:
    if is_str(val):
        # Mypy knows val is str
        print(val.upper())
    else:
        # Mypy knows val is int (Partitioning!)
        print(val + 1)
```

## Recipe: capability-based narrowing

Use `@runtime_checkable Protocol` with `TypeIs` for structural subtyping.

```python
from typing import Protocol, runtime_checkable
from typing_extensions import TypeIs

@runtime_checkable
class Reader(Protocol):
    def read(self) -> str: ...

def is_reader(val: object) -> TypeIs[Reader]:
    return isinstance(val, Reader)
```

## Best Practices

1. **Avoid `TypeGuard` for Booleans**: If your check is just "is this a string?", `TypeIs[str]` is always more precise.
2. **Handle Invariants**: If a type is "Never" (e.g. you've narrowed away all branches), use `assert_never(val)` from `typing_extensions` to prove your partitioning is exhaustive.
