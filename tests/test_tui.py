from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from textual.widgets import DataTable, Tree

from ruff_sync.cli import Arguments
from ruff_sync.tui.app import RuffSyncApp

if TYPE_CHECKING:
    import pathlib


@pytest.fixture
def mock_args(tmp_path: pathlib.Path) -> Arguments:
    return Arguments(
        command="inspect",
        upstream=(),
        to=tmp_path,
        exclude=(),
        verbose=0,
    )


def test_ruff_sync_app_init(mock_args: Arguments) -> None:
    app = RuffSyncApp(mock_args)
    assert app.args == mock_args
    assert app.config == {}


@pytest.mark.asyncio
async def test_ruff_sync_app_mount(mock_args: Arguments, tmp_path: pathlib.Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff]
line-length = 88
[tool.ruff.lint]
select = ["E", "F"]
""",
        encoding="utf-8",
    )

    app = RuffSyncApp(mock_args)
    async with app.run_test():
        assert app.config == {"line-length": 88, "lint": {"select": ["E", "F"]}}
        tree = app.query_one(Tree)
        assert tree.root.label.plain == "Local Configuration"
        # Check some children
        assert any(n.label.plain == "line-length" for n in tree.root.children)
        assert any(n.label.plain == "lint" for n in tree.root.children)


@pytest.mark.asyncio
async def test_ruff_sync_app_node_selection(mock_args: Arguments, tmp_path: pathlib.Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff]
line-length = 88
""",
        encoding="utf-8",
    )

    app = RuffSyncApp(mock_args)
    async with app.run_test() as pilot:
        tree = app.query_one(Tree)
        # Select "line-length"
        node = next(n for n in tree.root.children if n.label.plain == "line-length")
        tree.select_node(node)
        await pilot.pause()

        table = app.query_one(DataTable)
        # For a simple value, CategoryTable.update_content(88) adds row ("Value", "88")
        assert table.row_count == 1
        row = table.get_row_at(0)
        assert row == ["Value", "88"]


@pytest.mark.asyncio
async def test_ruff_sync_app_rule_selection(mock_args: Arguments, tmp_path: pathlib.Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff.lint]
select = ["RUF012"]
""",
        encoding="utf-8",
    )

    app = RuffSyncApp(mock_args)
    mock_markdown = "## RUF012 Documentation\n\nDetailed info here."

    with patch("ruff_sync.tui.widgets.get_ruff_rule_markdown", return_value=mock_markdown):
        async with app.run_test() as pilot:
            tree = app.query_one(Tree)
            # Find and select RUF012 node
            # It's inside tool.ruff -> lint -> select -> RUF012
            lint_node = next(n for n in tree.root.children if n.label.plain == "lint")
            lint_node.expand()
            await pilot.pause()

            select_node = next(n for n in lint_node.children if n.label.plain == "select")
            select_node.expand()
            await pilot.pause()

            rule_node = next(n for n in select_node.children if n.label.plain == "RUF012")
            tree.select_node(rule_node)
            await pilot.pause()

            inspector = app.query_one("#inspector")
            assert "hidden" not in inspector.classes
            # Wait for background fetch worker
            # Since we mocked it to return immediately, it should be fine
            # We might need to wait for worker completion if it was truly async

            # Textual's handle_node_selected calls fetch_and_display which is a @work(thread=True)
            # In run_test, we might need a small pause
            await pilot.pause(0.1)

            # Verify Markdown content (simplified check)
            # Textual's Markdown widget has a 'source' property
            assert "RUF012 Documentation" in str(inspector.source)
