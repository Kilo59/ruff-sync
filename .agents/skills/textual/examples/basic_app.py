"""A minimal Textual app boilerplate."""

from __future__ import annotations

from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Button, Footer, Header, Static
from typing_extensions import override


class BasicApp(App[None]):
    """A minimal Textual app boilerplate."""

    # v8.x.x: Specify a default theme
    theme = "nord"

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("q", "quit", "Quit application"),
        ("d", "toggle_dark", "Toggle Dark Mode"),
    ]

    CSS = """
    Screen {
        align: center middle;
    }

    Vertical {
        width: 30;
        height: auto;
        border: solid $accent;
        padding: 1;
    }

    Static {
        text-align: center;
        width: 100%;
        margin-bottom: 1;
    }

    /* v8.x.x: New pointer rule */
    Button {
        pointer: pointer;
    }
    """

    @override
    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()
        with Vertical():
            yield Static("Basic Textual App")
            yield Button("Click Me!", id="hello-btn", variant="primary")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "hello-btn":
            self.notify("Action Triggered!")


if __name__ == "__main__":
    BasicApp().run()
