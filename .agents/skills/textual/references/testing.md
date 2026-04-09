# Testing & Debugging

Textual apps are inherently asynchronous. Testing requires simulating user input and observing the UI state.

## Unit Testing with Pilot

Use the `pilot` object to interact with your app in a headless state.

```python
import pytest
from my_app import SimpleApp

@pytest.mark.asyncio
async def test_button_click():
    app = SimpleApp()
    async with app.run_test() as pilot:
        # Simulate a button click by CSS selector or ID
        await pilot.click("#say-hello-btn")

        # New in v8.x.x: Rapid clicks (double click)
        await pilot.click("#say-hello-btn", times=2)
        # OR use dedicated methods:
        await pilot.double_click("#say-hello-btn")
        await pilot.triple_click("#say-hello-btn")

        # Verify state
        assert app.notification_count >= 1
```

## Developer Tools

Textual includes powerful tools for live development.

### Textual Devtools
In one terminal, run:
```bash
textual console
```
In another, run your app with the `--dev` flag:
```bash
textual run --dev my_app.py
```
Logs and tracebacks will stream to the console, allowing you to see `self.log()` output and `print()` statements without breaking the UI.

## Procedures

### Simulating Text Entry
```python
async with app.run_test() as pilot:
    await pilot.press("h", "e", "l", "l", "o", "enter")
    assert app.query_one(Input).value == "hello"
```

### ⏳ Brittle Navigation & Expansion
When navigating complex structures like a `Tree` with many nodes:
- **Expansion Wait**: Expanding a node (`pilot.press("right")`) is asynchronous. If the number of child nodes is large, you MUST provide a significant `pilot.pause()` (e.g., 1.5s - 2.0s) before attempting to select or search for children.
- **Search-and-Verify**: Instead of fixed `down` counts, use a verification loop with a small `pilot.pause(0.02)` between steps to wait for cursor updates.

### 📸 Automated Screenshots (SVG)
When using `app.save_screenshot()` in a test:
- **Visibility Matters**: Only widgets and rows that are currently "scrolled into view" are captured in the SVG. Large tables or trees will be truncated unless you explicitly scroll.
- **Size Specification**: Define a repeatable terminal size in `run_test(size=(W, H))` to ensure consistent screenshot layouts across environments.

> [!IMPORTANT]
> Always use `pytest-asyncio` with the `@pytest.mark.asyncio` decorator for Textual tests. The boilerplate provided in `app.run_test()` handles the event loop lifecycle for you.
