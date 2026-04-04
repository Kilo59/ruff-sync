"""Widgets for the Ruff-Sync Terminal User Interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual import work
from textual.widgets import DataTable, Markdown, Tree
from typing_extensions import override

from ruff_sync.system import get_ruff_config_markdown, get_ruff_rule_markdown

if TYPE_CHECKING:
    from textual.widgets.tree import TreeNode


class ConfigTree(Tree[Any]):
    """A tree widget for navigating Ruff configuration."""

    def populate(self, config: dict[str, Any], has_rules: bool = False) -> None:
        """Populate the tree with configuration sections.

        Args:
            config: The unwrapped dictionary of Ruff configuration.
            has_rules: Whether to inject the 'Effective Active Rules' node.
        """
        self.clear()
        self.root.expand()
        if has_rules:
            self.root.add("Effective Active Rules", data="__rules__")
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

    @override
    def on_mount(self) -> None:
        """Initialize the table columns."""
        self.cursor_type = "row"
        self.add_columns("Key", "Value")

    def update_content(self, data: Any) -> None:
        """Update the table rows based on the selected data.

        Args:
            data: The data to display in the table.
        """
        self.clear(columns=True)
        self.add_columns("Key", "Value")
        if isinstance(data, dict):
            for key, value in sorted(data.items()):
                self.add_row(key, str(value))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self.add_row(str(i), str(item))
        else:
            self.add_row("Value", str(data))

    def update_rules(self, rules: list[dict[str, Any]]) -> None:
        """Update the table with a list of rules in multi-column format.

        Args:
            rules: The enriched rules list to display.
        """
        self.clear(columns=True)
        self.add_columns("Code", "Name", "Linter", "Status", "Fix")
        for rule in rules:
            status = rule.get("status", "Unknown")
            status_markup = status
            if status == "Enabled":
                status_markup = f"[green]{status}[/green]"
            elif status == "Ignored":
                status_markup = f"[red]{status}[/red]"

            fix = rule.get("fix_availability", "None")
            fix_markup = fix
            if fix == "Always":
                fix_markup = f"[cyan]{fix}[/cyan]"
            elif fix in ("Sometimes", "Enforced"):
                fix_markup = f"[yellow]{fix}[/yellow]"

            self.add_row(rule["code"], rule["name"], rule["linter"], status_markup, fix_markup)


class RuleInspector(Markdown):
    """A markdown widget for inspecting Ruff rules and settings."""

    _current_meta: ClassVar[dict[str, str]] = {}

    def on_mount(self) -> None:
        """Set initial placeholder content."""
        self.show_placeholder()

    def show_placeholder(self) -> None:
        """Display a placeholder message."""
        self.update(
            "## Selection Details\n\nSelect a configuration key in the tree or a rule "
            "code in the table to view documentation or additional context."
        )

    def show_context(self, path: str, value: Any) -> None:
        """Display general context for a configuration setting.

        Args:
            path: The full configuration path (e.g., 'tool.ruff.lint.select').
            value: The value of the setting.
        """
        # Show a summary for complex types, or the raw value for simple ones
        if isinstance(value, dict):
            summary = f"Table with {len(value)} keys"
        elif isinstance(value, list):
            summary = f"List with {len(value)} items"
        else:
            summary = f"`{value}`"

        self.update(f"### Configuration Context\n\n**Path**: `{path}`\n\n**Value**: {summary}")

    @work
    async def fetch_and_display(
        self, target: str, is_rule: bool = True, cached_content: str | None = None
    ) -> None:
        """Fetch and display the documentation for a rule or setting.

        Args:
            target: The Ruff rule code or configuration path.
            is_rule: True if fetching a rule, False if fetching a config setting.
            cached_content: Optional pre-fetched documentation to avoid subprocess calls.
        """
        if cached_content:
            self.update(cached_content.strip())
            return

        # Set a loading message
        desc = "rule" if is_rule else "config"
        self.update(f"## Inspecting {target}...\n\nFetching documentation from `ruff {desc}`...")

        if is_rule:
            content = await get_ruff_rule_markdown(target)
        else:
            content = await get_ruff_config_markdown(target)

        if content:
            self.update(content.strip())
        else:
            self.update(f"## Error\n\nCould not fetch documentation for {desc} `{target}`.")
