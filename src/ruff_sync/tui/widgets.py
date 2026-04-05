"""Widgets for the Ruff-Sync Terminal User Interface."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from textual import work
from textual.widgets import DataTable, Markdown, Tree
from typing_extensions import override

from ruff_sync.system import get_ruff_config_markdown, get_ruff_rule_markdown

if TYPE_CHECKING:
    from textual.widgets.tree import TreeNode

    from ruff_sync.models import RuffLinter, RuffRule


class ConfigTree(Tree[Any]):
    """A tree widget for navigating Ruff configuration."""

    def populate(
        self,
        config: dict[str, Any],
        has_rules: bool = False,
        linters: list[RuffLinter] | None = None,
        effective_rules: list[RuffRule] | None = None,
    ) -> None:
        """Populate the tree with configuration sections.

        Args:
            config: The unwrapped dictionary of Ruff configuration.
            has_rules: Whether to inject the 'Effective Rule Status' node.
            linters: Optional linter metadata for expanding the rules node.
            effective_rules: List of rules with status for filtering.
        """
        self.clear()
        self.root.expand()
        if has_rules:
            rules_node = self.root.add("Effective Rule Status", data="__rules__")
            if linters and effective_rules:
                self._populate_linter_nodes(rules_node, linters, effective_rules)
        self._populate_node(self.root, config)

        # Auto-expand up to 2 levels if it fits in the current view
        self._expand_if_fits()

    def _is_linter_active(self, linter: RuffLinter, effective_rules: list[RuffRule]) -> bool:
        """Check if a linter (or any of its categories) has active/ignored rules."""
        prefix = linter.get("prefix")
        if prefix and any(
            r["code"].startswith(prefix) and r["status"] != "Disabled" for r in effective_rules
        ):
            return True

        if "categories" in linter:
            return any(self._is_linter_active(c, effective_rules) for c in linter["categories"])

        return False

    def _populate_linter_nodes(
        self,
        parent: TreeNode[Any],
        linters: list[RuffLinter],
        effective_rules: list[RuffRule],
    ) -> None:
        """Recursively add linter category nodes to the tree."""
        # Sort linters by name for better navigation
        for linter in sorted(linters, key=lambda x: x["name"]):
            # Filter: only show if this linter or any category has active rules
            if not self._is_linter_active(linter, effective_rules):
                continue

            name = linter["name"]
            prefix = linter.get("prefix")
            label = f"{name} ({prefix})" if prefix else name

            # Use 'linter' structure in data for easy detection
            node_data = {"type": "linter", "prefix": prefix, "name": name}
            node = parent.add(label, data=node_data)

            # Recursive call for sub-categories (e.g. Pylint, pycodestyle)
            if "categories" in linter:
                self._populate_linter_nodes(node, linter["categories"], effective_rules)

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

    def _expand_if_fits(self) -> None:
        """Expand the first few levels of the tree if they fit in the vertical space."""
        # We target depth 2 expansion (Root -> Categories -> Items)
        target_depth = 2

        # Use widget height if available, otherwise fallback to a common terminal height
        # Subtract some margin for header/footer
        limit = (self.size.height or 24) - 2

        # Count visible nodes if we were to expand
        to_expand: list[TreeNode[Any]] = []
        visible_count = 1  # Start with the root

        def collect_nodes(node: TreeNode[Any], depth: int) -> int:
            nonlocal visible_count
            if depth >= target_depth:
                return visible_count

            children = list(node.children)
            if not children:
                return visible_count

            # If adding these children exceeds the limit, stop
            if visible_count + len(children) > limit:
                return visible_count

            # Mark for expansion and continue
            to_expand.append(node)
            visible_count += len(children)

            for child in children:
                collect_nodes(child, depth + 1)
            return visible_count

        collect_nodes(self.root, 0)

        # Apply the expansions
        for node in to_expand:
            node.expand()


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

    def update_rules(self, rules: list[RuffRule]) -> None:
        """Update the table with a list of rules using row-level highlighting.

        Args:
            rules: The enriched rules list to display.
        """
        self.clear(columns=True)
        # Status is now indicated by row highlighting (colors), so column is removed
        self.add_columns("Code", "Name", "Linter", "Fix")
        for rule in rules:
            status = rule.get("status", "Unknown")

            # Determine row color based on status
            color = ""
            if status == "Enabled":
                color = "success"
            elif status == "Ignored":
                color = "warning"
            elif status == "Disabled":
                color = (
                    "dim"  # Keep dim as it's a standard Rich style that works across backgrounds
                )

            # Rich uses [/] to close the nearest open tag
            code_markup = f"[{color}]{rule['code']}[/]" if color else rule["code"]
            name_markup = f"[{color}]{rule['name']}[/]" if color else rule["name"]

            fix = rule.get("fix_availability", "None")
            fix_markup = fix
            if fix == "Always":
                fix_markup = f"[accent]{fix}[/]"
            elif fix in ("Sometimes", "Enforced"):
                fix_markup = f"[warning]{fix}[/]"

            # Note: We still keep linter as-is for clarity
            self.add_row(code_markup, name_markup, rule["linter"], fix_markup, key=rule["code"])


class RuleInspector(Markdown):
    """A markdown widget for inspecting Ruff rules and settings."""

    _current_meta: ClassVar[dict[str, str]] = {}

    def on_mount(self) -> None:
        """Set initial placeholder content."""
        self.show_placeholder()

    @work(exclusive=True, group="inspector_update")
    async def show_placeholder(self) -> None:
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

    @work(exclusive=True, group="inspector_update")
    async def fetch_and_display(
        self,
        target: str,
        is_rule: bool = True,
        cached_content: str | None = None,
        rule_name: str | None = None,
        rule_status: str | None = None,
    ) -> None:
        """Fetch and display the documentation for a rule or setting.

        Args:
            target: The Ruff rule code or configuration path.
            is_rule: True if fetching a rule, False if fetching a config setting.
            cached_content: Optional pre-fetched documentation.
            rule_name: Optional rule name for display.
            rule_status: Optional rule status (Enabled, Ignored, Disabled).
        """
        if target == "tool.ruff":
            self.show_placeholder()
            return

        content: str | None = None
        if cached_content:
            content = cached_content
        else:
            # Set a loading message
            desc = "rule" if is_rule else "config"
            self.update(
                f"## Inspecting {target}...\n\nFetching documentation from `ruff {desc}`..."
            )

            if is_rule:
                content = await get_ruff_rule_markdown(target)
            else:
                content = await get_ruff_config_markdown(target)

        if content:
            # Prepend header if it's a rule
            header = ""
            if is_rule:
                status_icons = {"Enabled": "🟢", "Ignored": "🟡", "Disabled": "⚪"}
                icon = status_icons.get(rule_status or "Disabled", "⚪")
                name = rule_name or "Unknown Rule"
                header = f"# {icon} {target}: {name}\n\n---\n\n"

            self.update(header + content.strip())
        else:
            desc = "rule" if is_rule else "config"
            self.update(f"## Error\n\nCould not fetch documentation for {desc} `{target}`.")
