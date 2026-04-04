"""Screens for the Ruff-Sync Terminal User Interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from textual import on
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

if TYPE_CHECKING:
    from textual.app import ComposeResult

MAX_SEARCH_RESULTS: Final = 15


class OmniboxScreen(ModalScreen[str]):
    """A modal search screen for quickly finding Ruff rules."""

    CSS = """
    OmniboxScreen {
        align: center middle;
    }

    #omnibox-container {
        width: 60;
        height: auto;
        max-height: 20;
        background: $boost;
        border: thick $primary;
        padding: 1;
    }

    #omnibox-input {
        margin-bottom: 1;
    }

    #omnibox-results {
        height: auto;
        max-height: 12;
        border: none;
        background: $surface;
    }
    """

    def __init__(self, all_rules: list[dict[str, Any]], **kwargs: Any) -> None:
        """Initialize the search screen.

        Args:
            all_rules: The list of all rules to search through.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(**kwargs)
        self.all_rules = all_rules

    def compose(self) -> ComposeResult:
        """Compose the search interface."""
        with Vertical(id="omnibox-container"):
            yield Static("[b]Search Ruff Rules[/b] (e.g. F401, unused)", id="omnibox-title")
            yield Input(placeholder="Start typing...", id="omnibox-input")
            yield OptionList(id="omnibox-results")

    def on_mount(self) -> None:
        """Focus the input on mount."""
        self.query_one(Input).focus()

    @on(Input.Changed)
    def handle_input_changed(self, event: Input.Changed) -> None:
        """Filter rules based on search input.

        Args:
            event: The input changed event.
        """
        search_query = event.value.strip().lower()
        results_list = self.query_one(OptionList)
        results_list.clear_options()

        if not search_query:
            return

        matches = []
        for rule in self.all_rules:
            code = rule["code"].lower()
            name = rule["name"].lower()
            if search_query in code or search_query in name:
                matches.append(rule)
                if len(matches) >= MAX_SEARCH_RESULTS:  # Limit results
                    break

        for match in matches:
            results_list.add_option(
                Option(f"[b]{match['code']}[/b] - {match['name']}", id=match["code"])
            )

    @on(Input.Submitted)
    def handle_input_submitted(self) -> None:
        """Handle enter key in the input."""
        results_list = self.query_one(OptionList)
        if results_list.option_count > 0:
            # If there's a selected option, use it. Otherwise use the first matching one.
            index = results_list.highlighted if results_list.highlighted is not None else 0
            option = results_list.get_option_at_index(index)
            if option.id:
                self.dismiss(str(option.id))

    @on(OptionList.OptionSelected)
    def handle_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle selection from the results list."""
        if event.option.id:
            self.dismiss(str(event.option.id))

    def action_cancel(self) -> None:
        """Close the screen without selection."""
        self.dismiss()
