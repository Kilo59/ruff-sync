---
name: textual
description: Build sophisticated Terminal User Interfaces (TUIs) in Python using an async, CSS-inspired framework.
---

# Textual TUI Framework (>=8.2.2)

Textual is a Python framework for creating interactive, beautiful Terminal User Interfaces (TUIs). It uses an asynchronous engine and a layout system inspired by modern web development (Flexbox/Grid and CSS).

## Quick Start

```python
from __future__ import annotations
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static

class SimpleApp(App[None]):
    """A minimal Textual app."""
    BINDINGS = [("q", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Hello, [bold blue]Textual[/bold blue]!")
        yield Footer()

if __name__ == "__main__":
    SimpleApp().run()
```

## Core Workflow

1. **`compose()`**: Define the UI structure by `yield`-ing widgets.
2. **Styling**: Use **TCSS** (Textual Cascading Style Sheets) for layout and design.
3. **Event Handlers**: Handle interaction via specially named methods (e.g., `on_button_pressed`).
4. **Reactivity**: Use `reactive` attributes to automatically update the UI when data changes.

## Progressive Disclosure (Detailed References)

- [**Styling & Layout**](references/styling.md): TCSS, Flexbox, Grid, and Units.
- [**Events & Reactivity**](references/events.md): Message passing, watchers, and state management.
- [**Widget Library**](references/widgets.md): Common components (DataTable, Input, ListView).
- [**Testing**](references/testing.md): Unit testing apps with `pilot` and `App.run_test`.

## Gotchas & Breaking Changes (>=8.2.2)

> [!WARNING]
> - **8.2.2 Breaking Changes**:
>   - `Static.renderable` and `Label.renderable` are now **`Static.content`** and **`Label.content`**.
>   - `Select.BLANK` is now **`Select.NULL`**.
> - **Fractional Units**: Use `fr` for fractional units (e.g. `width: 1fr`). A common typo is `rf`, which is invalid.
> - **Async Handlers**: Event handlers can be `async def` or `def`. Use `async` if you need to `await` I/O or `post_message`.
> - **Main Thread**: Do not block the main thread with long-running synchronous code. Use `self.run_worker()` for background tasks.
- **Theme Tokens in Rich Markup**: Textual theme tokens (e.g., `$success`, `$accent`) **cannot** be used directly in Rich markup strings (like in `DataTable` cells). They must be resolved to hex strings at runtime: `str(self.app.get_theme(self.app.theme).success)`.
- **Type-Safe Queries (No Cast)**: If `typing.cast` is banned (e.g. by `TID251`), use a variable annotation with a targeted `# type: ignore` to resolve `query_one` results:
  ```python
  tree: MyTree = app.query_one("#tree-id")  # type: ignore[assignment]
  ```
