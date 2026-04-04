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

        # Verify state
        assert app.notification_count == 1

        # Take a screenshot for debugging
        # pilot.app.save_screenshot("test_click.svg")
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

### Waiting for Animations/I/O
If your UI has transitions or performs background work, use `pilot.wait_for_scheduled_animations()` or simply `await pilot.pause(0.1)`.

> [!IMPORTANT]
> Always use `pytest-asyncio` with the `@pytest.mark.asyncio` decorator for Textual tests. The boilerplate provided in `app.run_test()` handles the event loop lifecycle for you.
