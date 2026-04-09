"""Main application logic for the Ruff Inspect Terminal User Interface."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar, Final

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Tree
from typing_extensions import override

from ruff_sync.config_io import load_local_ruff_config
from ruff_sync.system import compute_effective_rules, get_all_ruff_rules, get_ruff_linters
from ruff_sync.tui.constants import RULE_PATTERN
from ruff_sync.tui.screens import LegendScreen, OmniboxScreen
from ruff_sync.tui.themes import AMBER_EMBER
from ruff_sync.tui.types_ import ConfigNode, LinterNode, RulesCollectionNode, wrap_data
from ruff_sync.tui.widgets import CategoryTable, ConfigTree, RuleInspector

if TYPE_CHECKING:
    from ruff_sync.cli import Arguments
    from ruff_sync.types_ import RuffLinter, RuffRule


LOGGER = logging.getLogger(__name__)

MIN_RULE_COLUMNS: Final = 4


class RuffSyncApp(App[None]):
    """Ruff Inspect Terminal User Interface."""

    TITLE = "Ruff Inspect"

    CSS = """
    Screen {
        background: $surface;
    }

    #config-tree {
        width: 1fr;
        max-width: 42;
        height: 100%;
        border-right: solid $primary-darken-2;
    }

    #content-pane {
        width: 1fr;
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
        ("?", "show_legend", "Show Legend"),
        ("l", "show_legend", "Show Legend"),
        ("c", "copy_content", "Copy Content"),
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
        self.all_rules: list[RuffRule] = []
        self.effective_rules: list[RuffRule] = []
        self.linters: list[RuffLinter] = []

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
        root_node = wrap_data("tool.ruff", self.config)
        tree.populate(root_node)
        tree.focus()

        # Register and set the default theme
        self.register_theme(AMBER_EMBER)
        self.theme = "amber-ember"

        # Prime the caches in the background
        self._prime_caches()

    @work
    async def _prime_caches(self) -> None:
        """Fetch rules and compute effectiveness in the background."""
        self.all_rules = await get_all_ruff_rules()
        self.linters = await get_ruff_linters()
        if self.config:
            self.effective_rules = compute_effective_rules(self.all_rules, self.config)

        # Refresh the tree once metadata is loaded to show linter groups
        tree = self.query_one(ConfigTree)
        root_node = wrap_data("tool.ruff", self.config)
        rules_node = RulesCollectionNode(self.linters, self.effective_rules)
        tree.populate(root_node, rules_node)

    @on(Tree.NodeSelected)
    def handle_node_selected(self, event: Tree.NodeSelected[Any]) -> None:
        """Handle tree node selection.

        Args:
            event: The tree node selected event.
        """
        node = event.node.data
        if not isinstance(node, ConfigNode):
            return

        table = self.query_one(CategoryTable)
        inspector = self.query_one(RuleInspector)

        table.render_node(node)

        target, doc_type = node.doc_target()

        if doc_type == "none":
            if isinstance(node, RulesCollectionNode):
                inspector.update(
                    "## Effective Rule Status\n\n"
                    "This table shows rules that are actively being used "
                    "or have been explicitly ignored in your configuration."
                )
            elif isinstance(node, LinterNode):
                name = node.linter["name"]
                prefix = node.linter.get("prefix", "")
                msg = (
                    f"## {name} ({prefix or 'No Prefix'})\n\nShowing rules for the {name} category."
                )
                inspector.update(msg)
            elif getattr(node, "path", "") == "tool.ruff":
                inspector.show_placeholder()
        elif doc_type == "rule":
            self._inspect_rule(target)
        elif doc_type == "config":
            inspector.fetch_and_display(target, is_rule=False)

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
            # Use row_key for stable rule code extraction (avoids markup)
            rule_code = str(event.row_key.value)
            self._inspect_rule(rule_code)
            return

        key, value = row
        # Check if the value or key looks like a rule code
        rule_code_from_kv = None
        if RULE_PATTERN.match(str(key)):
            rule_code_from_kv = str(key)
        elif RULE_PATTERN.match(str(value)):
            rule_code_from_kv = str(value)

        if rule_code_from_kv:
            self._inspect_rule(rule_code_from_kv)
        else:
            # It's a configuration key, show its documentation
            inspector = self.query_one(RuleInspector)

            cursor_node = self.query_one(ConfigTree).cursor_node
            if cursor_node:
                node_data = cursor_node.data
                if isinstance(node_data, ConfigNode):
                    # For lists/dicts the key might be index or dict key
                    full_path = (
                        f"{node_data.path}.{key}"
                        if not key.startswith("[")
                        else f"{node_data.path}{key}"
                    )
                    inspector.fetch_and_display(full_path, is_rule=False)

    def _inspect_rule(self, rule_code: str) -> None:
        """Centralized helper for rule inspection with metadata enrichment.

        Args:
            rule_code: The Ruff rule code to inspect.
        """
        # Fetch metadata for enrichment
        rule_data = next((r for r in self.effective_rules if r["code"] == rule_code), None)
        name = rule_data.get("name") if rule_data else None
        status = str(rule_data.get("status", "Disabled")) if rule_data else "Disabled"
        explanation = rule_data.get("explanation") if rule_data else None
        fix = rule_data.get("fix_availability") if rule_data else None

        inspector = self.query_one(RuleInspector)
        inspector.fetch_and_display(
            rule_code,
            is_rule=True,
            cached_content=explanation,
            rule_name=name,
            rule_status=status,
            fix_availability=fix,
        )

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
            self._inspect_rule(rule_code)

    def action_show_legend(self) -> None:
        """Display the TUI legend modal."""
        self.push_screen(LegendScreen())

    def action_copy_content(self) -> None:
        """Copy the current inspector content to the clipboard."""
        inspector = self.query_one(RuleInspector)
        if inspector.source:
            self.copy_to_clipboard(str(inspector.source))
            self.notify("Copied content to clipboard", title="Clipboard")
        else:
            self.notify("No content to copy", severity="warning")
