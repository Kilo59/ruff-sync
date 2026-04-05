"""Demonstrating Textual's reactive system."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Static
from typing_extensions import override


class ReactiveApp(App[None]):
    """Demonstrating Textual's reactive system."""

    # Reactive attribute: UI can respond to changes automatically
    search_query: reactive[str] = reactive("")

    CSS = """
    #status {
        background: $primary;
        color: $text;
        /* v8.x.x: Simplified padding for text content */
        text-padding: 1 2;
        margin-top: 1;
        width: 100%;
        text-align: center;
    }
    """

    @override
    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header()
        with Container():
            yield Input(placeholder="Type to search...", id="search-input")
            yield Static("Waiting for input...", id="status")
        yield Footer()

    def watch_search_query(self, query: str) -> None:
        """Called automatically when search_query changes."""
        # Use child type selector to return a Static widget
        status = self.query_one("#status", Static)
        if query:
            status.update(f"Searching for: [bold]{query}[/bold]")
        else:
            status.update("Waiting for input...")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Update reactive state on input."""
        self.search_query = event.value


if __name__ == "__main__":
    ReactiveApp().run()
