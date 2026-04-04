"""Widgets for the Ruff-Sync Terminal User Interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from textual import work
from textual.widgets import DataTable, Markdown, Tree

from ruff_sync.system import get_ruff_rule_markdown

if TYPE_CHECKING:
    from textual.widgets.tree import TreeNode


class ConfigTree(Tree[Any]):
    """A tree widget for navigating Ruff configuration."""

    def populate(self, config: dict[str, Any]) -> None:
        """Populate the tree with configuration sections.

        Args:
            config: The unwrapped dictionary of Ruff configuration.
        """
        self.clear()
        self.root.expand()
        self._populate_node(self.root, config)

    def _populate_node(self, parent: TreeNode[Any], data: Any) -> None:
        """Recursively add nodes to the tree.

        Args:
            parent: The parent tree node.
            data: The data to add to the tree.
        """
        if isinstance(data, dict):
            for key, value in sorted(data.items()):
                node = parent.add(key, data=value)
                if isinstance(value, (dict, list)):
                    self._populate_node(node, value)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                label = str(item) if not isinstance(item, (dict, list)) else f"[{i}]"
                node = parent.add(label, data=item)
                if isinstance(item, (dict, list)):
                    self._populate_node(node, item)


class CategoryTable(DataTable[Any]):
    """A table widget for displaying configuration keys and values."""

    def on_mount(self) -> None:
        """Initialize the table columns."""
        self.cursor_type = "row"
        self.add_columns("Key", "Value")

    def update_content(self, data: Any) -> None:
        """Update the table rows based on the selected data.

        Args:
            data: The data to display in the table.
        """
        self.clear()
        if isinstance(data, dict):
            for key, value in sorted(data.items()):
                self.add_row(key, str(value))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self.add_row(str(i), str(item))
        else:
            self.add_row("Value", str(data))


class RuleInspector(Markdown):
    """A markdown widget for inspecting Ruff rules."""

    @work(thread=True)
    async def fetch_and_display(self, rule_code: str) -> None:
        """Fetch and display the documentation for a rule.

        Args:
            rule_code: The Ruff rule code to fetch documentation for.
        """
        # Set a loading message
        self.update(f"## Inspecting {rule_code}...\n\nFetching documentation from `ruff rule`...")

        content = await get_ruff_rule_markdown(rule_code)

        if content:
            self.update(content)
        else:
            self.update(f"## Error\n\nCould not fetch documentation for rule `{rule_code}`.")
