"""Main application logic for the Ruff-Sync Terminal User Interface."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar, Final

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Tree
from typing_extensions import override

from ruff_sync.config_io import load_local_ruff_config
from ruff_sync.system import compute_effective_rules, get_all_ruff_rules
from ruff_sync.tui.constants import RULE_PATTERN
from ruff_sync.tui.screens import OmniboxScreen
from ruff_sync.tui.widgets import CategoryTable, ConfigTree, RuleInspector

if TYPE_CHECKING:
    from ruff_sync.cli import Arguments


LOGGER = logging.getLogger(__name__)

MIN_RULE_COLUMNS: Final = 4


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
        height: 40%;
        border-bottom: solid $primary-darken-2;
    }

    #inspector {
        height: 60%;
        padding: 1;
        background: $surface-darken-1;
        overflow-y: auto;
    }
    """

    BINDINGS: ClassVar[list[Any]] = [
        ("q", "quit", "Quit"),
        ("/", "search", "Search Rules"),
        ("enter", "select", "View Details"),
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
        self.all_rules: list[dict[str, Any]] = []
        self.effective_rules: list[dict[str, Any]] = []

    @override
    def compose(self) -> ComposeResult:
        """Compose the user interface elements."""
        yield Header()
        with Horizontal():
            yield ConfigTree("Local Configuration", id="config-tree")
            with Vertical(id="content-pane"):
                yield CategoryTable(id="category-table")
                yield RuleInspector(id="inspector")
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
        tree.populate(self.config, has_rules=True)
        tree.focus()

        # Prime the caches in the background
        self._prime_caches()

    @work
    async def _prime_caches(self) -> None:
        """Fetch rules and compute effectiveness in the background."""
        self.all_rules = await get_all_ruff_rules()
        if self.config:
            self.effective_rules = compute_effective_rules(self.all_rules, self.config)

    @work
    async def _display_effective_rules(self) -> None:
        """Populate the table with the effective rules list."""
        if not self.all_rules:
            self.all_rules = await get_all_ruff_rules()
            self.effective_rules = compute_effective_rules(self.all_rules, self.config)

        # Filter for only Enabled or Ignored rules as per the "Effective Rules" proposal
        effective_only = [r for r in self.effective_rules if r["status"] != "Disabled"]

        table = self.query_one(CategoryTable)
        table.update_rules(effective_only)

        inspector = self.query_one(RuleInspector)
        inspector.update(
            "## Effective Rule Status\n\nThis table shows rules that are actively being used "
            "or have been explicitly ignored in your configuration."
        )

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

        if data == "__rules__":
            self._display_effective_rules()
            return

        # Build full path for context
        full_path = self._get_node_path(event.node)

        # Check if the node label or path matches a ruff rule
        if isinstance(label_text, str) and RULE_PATTERN.match(label_text):
            inspector.fetch_and_display(label_text, is_rule=True)
        elif isinstance(data, (dict, list)):
            table.update_content(data)
            # Fetch config documentation for the section if possible
            inspector.fetch_and_display(full_path, is_rule=False)
        else:
            table.update_content(data)
            inspector.fetch_and_display(full_path, is_rule=False)

    @on(DataTable.RowSelected)
    def handle_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle data table row selection.

        Args:
            event: The data table row selected event.
        """
        table = self.query_one(CategoryTable)
        row = table.get_row_at(event.cursor_row)

        # Handle multi-column rules view vs key-value view
        if len(row) >= MIN_RULE_COLUMNS:
            rule_code = str(row[0])
            # Check for cached explanation
            rule_data = next((r for r in self.all_rules if r["code"] == rule_code), None)
            explanation = rule_data.get("explanation") if rule_data else None

            inspector = self.query_one(RuleInspector)
            inspector.fetch_and_display(rule_code, is_rule=True, cached_content=explanation)
            return

        key, value = row
        # Check if the value or key looks like a rule code
        rule_code = None
        if RULE_PATTERN.match(str(key)):
            rule_code = str(key)
        elif RULE_PATTERN.match(str(value)):
            rule_code = str(value)

        if rule_code:
            inspector = self.query_one(RuleInspector)
            inspector.fetch_and_display(rule_code, is_rule=True)
        else:
            # It's a configuration key, show its documentation
            inspector = self.query_one(RuleInspector)
            full_path = f"{self._get_node_path(self.query_one(ConfigTree).cursor_node)}.{key}"
            inspector.fetch_and_display(full_path, is_rule=False)

    def _get_node_path(self, node: Any) -> str:
        """Construct the full configuration path to a tree node.

        Args:
            node: The tree node.

        Returns:
            The dot-separated configuration path.
        """
        path: list[str] = []
        current = node
        while current and current != self.query_one(ConfigTree).root:
            label = current.label
            label_text = str(label.plain) if hasattr(label, "plain") else str(label)
            path.append(label_text)
            current = current.parent
        return "tool.ruff." + ".".join(reversed(path)) if path else "tool.ruff"

    def action_search(self) -> None:
        """Launch the global fuzzy search Omnibox."""
        if not self.all_rules:
            self.notify("Still fetching rule metadata...", severity="warning")
            # Even if empty, we push; the screen handles empty list
        self.push_screen(OmniboxScreen(self.all_rules), self.handle_omnibox_result)

    def handle_omnibox_result(self, rule_code: str | None) -> None:
        """Handle the result from the Omnibox search.

        Args:
            rule_code: The selected rule code, or None if cancelled.
        """
        if rule_code:
            rule_data = next((r for r in self.all_rules if r["code"] == rule_code), None)
            explanation = rule_data.get("explanation") if rule_data else None

            inspector = self.query_one(RuleInspector)
            inspector.fetch_and_display(rule_code, is_rule=True, cached_content=explanation)
