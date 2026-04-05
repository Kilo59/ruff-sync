# Refactoring Patterns (Replacing `isinstance`)

Overuse of `isinstance` is an anti-pattern. Use these design patterns to replace runtime checks with static type safety.

## 5. The Generics Spectrum (Healthy to Toxic)

Generics are a powerful tool for clarity. Use this spectrum to decide when to abstract and when to stay pragmatic.

### Level 1: Healthy (Highly Encouraged)
Simple containers or return types that provide immediate clarity over `Any`.

**Example**:
```python
T = TypeVar("T")

class Result(Generic[T]):
    def __init__(self, value: T) -> None:
        self.value = value

# Result[Project] is 10x clearer than Mapping[str, object].
```

### Level 2: Robust (Recommended for Interfaces)
Bound TypeVars that restrict a Generic to a specific hierarchy or protocol.

**Example**:
```python
T = TypeVar("T", bound=Mapping[str, object])

def merge_configs(base: T, update: T) -> T:
    # Guaranteed to return the same specific type (e.g. Table).
    ...
```

### Level 3: Strategic vs. Toxic (The ROI Decision)
The most complex type signatures are only justified if they **Shift Complexity** from the features to the infrastructure.

#### Level 3: Strategic (High ROI)
High complexity is a valuable investment if it:
- **Protects Critical Logic**: core merge engines, security/path boundaries.
- **Simplifies Downstream**: Removes the need for narrowing at 5+ call sites.
- **Public APIs**: Ensures third-party authors get absolute type safety.

#### Level 3: Toxic (Low ROI)
High complexity is a liability if it:
- **Obfuscates Simple Tasks**: e.g., recursive protocols for non-recursive data.
- **Increases Total Debt**: Used in one-off CLI code, TUI layout, or test utilities.
- **Breaks the 10-Second Rule**: Without a corresponding "Downstream Payoff."

---

## 6. Refactoring Red Flags (When to Stop)

Stop refactoring and use a simple `isinstance` or `# type: ignore[code]` if:
- **Generic Explosion**: Adding a `TypeVar` requires updating 5+ unrelated call sites.
- **Human-Readability**: If a signature requires more than 3 `TypeVar` or complex variance and it's NOT a core library function.
- **3rd-Party Conflict**: If a refactor requires importing a protocol that creates a cycle or breaks structural compatibility with a library like `tomlkit`.

**"Pragmatic but Safe" (Better for ruff-sync Features)**:
```python
from typing import Mapping

def deep_navigate(data: Mapping[str, object], path: list[str]) -> Optional[str]:
    # Navigate using a simple loop and isinstance narrowing.
    # Type-safe, human-readable, and 100x easier to maintain.
    current: object = data
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, str) else None
```
