"""Main application logic for the Ruff-Sync Terminal User Interface."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Tree
from typing_extensions import override

from ruff_sync.config_io import load_local_ruff_config
from ruff_sync.tui.constants import RULE_PATTERN
from ruff_sync.tui.widgets import CategoryTable, ConfigTree, RuleInspector

if TYPE_CHECKING:
    from ruff_sync.cli import Arguments


LOGGER = logging.getLogger(__name__)


class RuffSyncApp(App[None]):
    """Ruff-Sync Terminal User Interface."""

    CSS = """
    Screen {
        background: $surface;
    }

    #config-tree {
        width: 1fr;
        height: 100%;
        border-right: solid $primary-darken-2;
    }

    #content-pane {
        width: 2fr;
        height: 100%;
    }

    #category-table {
        height: 1fr;
        border-bottom: solid $primary-darken-2;
    }

    #inspector {
        height: 1fr;
        padding: 1;
        background: $surface-darken-1;
    }

    .hidden {
        display: none;
    }
    """

    BINDINGS: ClassVar[list[Any]] = [
        ("q", "quit", "Quit"),
        ("/", "focus('config-tree')", "Search"),
    ]

    def __init__(self, args: Arguments, **kwargs: Any) -> None:
        """Initialize the application.

        Args:
            args: The CLI arguments.
            **kwargs: Additional keyword arguments.
        """
        super().__init__(**kwargs)
        self.args = args
        self.config: dict[str, Any] = {}

    @override
    def compose(self) -> ComposeResult:
        """Compose the user interface elements."""
        yield Header()
        with Horizontal():
            yield ConfigTree("Local Configuration", id="config-tree")
            with Vertical(id="content-pane"):
                yield CategoryTable(id="category-table")
                yield RuleInspector(id="inspector", classes="hidden")
        yield Footer()

    async def on_mount(self) -> None:
        """Load the configuration and populate the tree."""
        try:
            self.config = load_local_ruff_config(self.args.to)
        except Exception:
            LOGGER.exception("Failed to load Ruff configuration.")
            self.notify("Failed to load Ruff configuration.", severity="error")
            self.config = {}

        tree = self.query_one(ConfigTree)
        tree.populate(self.config)
        tree.focus()

    @on(Tree.NodeSelected)
    def handle_node_selected(self, event: Tree.NodeSelected[Any]) -> None:
        """Handle tree node selection.

        Args:
            event: The tree node selected event.
        """
        data = event.node.data
        label = event.node.label
        label_text = str(label.plain) if hasattr(label, "plain") else str(label)

        table = self.query_one(CategoryTable)
        inspector = self.query_one(RuleInspector)

        # Basic rule code detection (e.g., PIE790, RUF012)
        if isinstance(label_text, str) and RULE_PATTERN.match(label_text):
            inspector.remove_class("hidden")
            inspector.fetch_and_display(label_text)
        elif isinstance(data, (dict, list)):
            inspector.add_class("hidden")
            table.update_content(data)
        else:
            inspector.add_class("hidden")
            table.update_content(data)

    @on(DataTable.RowSelected)
    def handle_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle data table row selection.

        Args:
            event: The data table row selected event.
        """
        table = self.query_one(CategoryTable)
        row = table.get_row_at(event.cursor_row)
        key, value = row

        # Check if the value or key looks like a rule code
        rule_code = None
        if RULE_PATTERN.match(str(key)):
            rule_code = str(key)
        elif RULE_PATTERN.match(str(value)):
            rule_code = str(value)

        if rule_code:
            inspector = self.query_one(RuleInspector)
            inspector.remove_class("hidden")
            inspector.fetch_and_display(rule_code)
