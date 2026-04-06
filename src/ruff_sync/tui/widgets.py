"""Widgets for the Ruff-Sync Terminal User Interface."""

from __future__ import annotations

from functools import singledispatchmethod
from typing import TYPE_CHECKING, Any, ClassVar

from textual import work
from textual.widgets import DataTable, Markdown, Tree
from typing_extensions import override

from ruff_sync.system import get_ruff_config_markdown, get_ruff_rule_markdown
from ruff_sync.tui.types_ import (
    ConfigNode,
    DictNode,
    LinterNode,
    ListNode,
    RulesCollectionNode,
    ScalarNode,
)

if TYPE_CHECKING:
    from textual.widgets.tree import TreeNode

    from ruff_sync.types_ import RuffRule


class ConfigTree(Tree[Any]):
    """A tree widget for navigating Ruff configuration."""

    def populate(
        self,
        root_node: ConfigNode,
        rules_node: ConfigNode | None = None,
    ) -> None:
        """Populate the tree using ConfigNode types."""
        self.clear()
        self.root.expand()
        if rules_node:
            node = self.root.add(rules_node.key, data=rules_node)
            self._populate_node(node, rules_node)

        self._populate_node(self.root, root_node)

        # Auto-expand up to 2 levels if it fits in the current view
        self._expand_if_fits()

    def _populate_node(self, parent: TreeNode[Any], data: ConfigNode) -> None:
        """Recursively add ConfigNode children to the tree."""
        for child in data.children():
            node = parent.add(child.key, data=child)
            if child.children():
                self._populate_node(node, child)

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

    def _reset_columns(self, *cols: str) -> None:
        """Clear the table and add the specified columns."""
        self.clear(columns=True)
        self.add_columns(*cols)

    @singledispatchmethod
    def render_node(self, node: Any) -> None:
        """Fallback for unhandled nodes."""
        self._reset_columns("Key", "Value")

    @render_node.register
    def _(self, node: DictNode) -> None:
        self._reset_columns("Key", "Value")
        for key, value in sorted(node.data.items()):
            self.add_row(key, str(value))

    @render_node.register
    def _(self, node: ListNode) -> None:
        self._reset_columns("Key", "Value")
        for i, item in enumerate(node.data):
            self.add_row(str(i), str(item))

    @render_node.register
    def _(self, node: ScalarNode) -> None:
        self._reset_columns("Key", "Value")
        self.add_row("Value", str(node.value))

    @render_node.register
    def _(self, node: RulesCollectionNode) -> None:
        self._reset_columns("Code", "Name", "Linter", "Fix")
        effective_only = [r for r in node.effective_rules if r["status"] != "Disabled"]
        self._render_rules(effective_only)

    @render_node.register
    def _(self, node: LinterNode) -> None:
        self._reset_columns("Code", "Name", "Linter", "Fix")
        prefix = node.linter.get("prefix", "")
        filtered = [r for r in node.effective_rules if r["code"].startswith(prefix)]
        self._render_rules(filtered)

    def _render_rules(self, rules: list[RuffRule]) -> None:
        """Render a list of rules in the table with theme-aware highlighting."""
        # Resolve theme colors to hex strings for Rich markup safely
        success_clr = "green"
        warning_clr = "yellow"
        accent_clr = "magenta"

        try:
            # We can access the theme via the App instance
            theme = self.app.get_theme(self.app.theme)
            if theme:
                success_clr = str(theme.success)
                warning_clr = str(theme.warning)
                accent_clr = str(theme.accent)
        except (AttributeError, KeyError):
            # Fallback for headless tests or if the app is not yet initialized
            pass

        for rule in rules:
            status = rule.get("status", "Unknown")

            # Determine row color based on status
            color = ""
            if status == "Enabled":
                color = success_clr
            elif status == "Ignored":
                color = warning_clr
            elif status == "Disabled":
                color = "dim"

            # Rich uses [/] to close the nearest open tag
            code_markup = f"[{color}]{rule['code']}[/]" if color else rule["code"]
            name_markup = f"[{color}]{rule['name']}[/]" if color else rule["name"]

            fix = rule.get("fix_availability", "None")
            fix_markup = fix
            if fix == "Always":
                fix_markup = f"[{accent_clr}]{fix}[/]"
            elif fix in ("Sometimes", "Enforced"):
                fix_markup = f"[{warning_clr}]{fix}[/]"

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

    def show_context(self, node: ConfigNode) -> None:
        """Display general context for a configuration setting."""
        # Use single dispatch or node attributes
        if isinstance(node, DictNode):
            summary = f"Table with {len(node.data)} keys"
        elif isinstance(node, ListNode):
            summary = f"List with {len(node.data)} items"
        elif isinstance(node, ScalarNode):
            summary = f"`{node.value}`"
        else:
            summary = "Unknown type"

        self.update(f"### Configuration Context\n\n**Path**: `{node.path}`\n\n**Value**: {summary}")

    @work(exclusive=True, group="inspector_update")
    async def fetch_and_display(
        self,
        target: str,
        is_rule: bool = True,
        cached_content: str | None = None,
        rule_name: str | None = None,
        rule_status: str | None = None,
        matching_select: str | None = None,
        matching_ignore: str | None = None,
        fix_availability: str | None = None,
    ) -> None:
        """Fetch and display the documentation for a rule or setting.

        Args:
            target: The Ruff rule code or configuration path.
            is_rule: True if fetching a rule, False if fetching a config setting.
            cached_content: Optional pre-fetched documentation.
            rule_name: Optional rule name for display.
            rule_status: Optional rule status (Enabled, Ignored, Disabled).
            matching_select: Optional prefix that matched in select.
            matching_ignore: Optional prefix that matched in ignore.
            fix_availability: Optional fix availability information.
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
                header = f"# {icon} {target}: {name}\n\n"

                # Status and Selection details
                status_parts = [f"**Status**: {rule_status}"]
                if matching_select or matching_ignore:
                    details = []
                    if matching_select:
                        details.append(f"selected via `{matching_select}`")
                    if matching_ignore:
                        details.append(f"ignored via `{matching_ignore}`")

                    if details:
                        status_parts.append(f"({', but '.join(details)})")

                header += " ".join(status_parts)

                if fix_availability:
                    header += f" | **Fix**: {fix_availability}"

                header += "\n\n---\n\n"

            self.update(header + content.strip())
        else:
            desc = "rule" if is_rule else "config"
            self.update(f"## Error\n\nCould not fetch documentation for {desc} `{target}`.")
