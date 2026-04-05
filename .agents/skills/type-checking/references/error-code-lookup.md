# Mypy Error Code Lookup Table

Match the Mypy error code from your terminal to the project-safe resolution pattern.

| Error Code | Meaning | Project-Safe Resolution |
| :--- | :--- | :--- |
| **`[attr-defined]`** | Attribute not found on base class. | Use `isinstance(obj, SubClass)` or a `Protocol`. |
| **`[union-attr]`** | Attribute exists on one type in Union, but not all. | Narrow with `isinstance` or `TypeIs`. |
| **`[index]`** | Indexing an object that isn't a mapping/sequence. | Narrow to `Mapping` or `Sequence`. |
| **`[arg-type]`** | Passing a type that is too broad to a function. | Partition the union with `TypeIs`. |
| **`[assignment]`** | Assigning an incompatible type (e.g. from a proxy). | Narrow *before* assignment, or use `Any` + `Protocol`. |
| **`[unreachable]`** | Mypy thinks code is logically impossible. | Use `reveal_type` to see the "stale" narrowing. |

## Detailed Recipes

### Fixing `[union-attr]` (The most common error)

**Bad (Cast)**:
```python
val = get_union() # str | None
val.upper()       # [union-attr] "None" has no attribute "upper"
# NO: val = cast(str, val)
```

**Good (Narrowing)**:
```python
val = get_union()
if val is not None:
    val.upper() # FIXED
```

### Fixing `[assignment]` (Dealing with `tomlkit` or `Any`)

**Bad (Cast)**:
```python
doc = tomlkit.parse(...)
tool: Table = doc["tool"] # [assignment] Incompatible types (Item vs Table)
# NO: tool = cast(Table, doc["tool"])
```

**Good (Narrowing)**:
```python
doc = tomlkit.parse(...)
tool = doc.get("tool")
if not isinstance(tool, Table):
    raise TypeError("Missing [tool] table")
# tool is now Table
```

### Fixing `[arg-type]` (Narrowing for function calls)

**Bad (Cast)**:
```python
def process_str(s: str): ...
data: Union[str, int] = ...
process_str(data) # [arg-type] Argument 1 has incompatible type
# NO: process_str(cast(str, data))
```

**Good (TypeIs)**:
```python
from typing_extensions import TypeIs

def is_str(v: object) -> TypeIs[str]:
    return isinstance(v, str)

if is_str(data):
    process_str(data) # FIXED
```
