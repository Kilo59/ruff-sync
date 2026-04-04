from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import patch

import pytest
from textual.widgets import DataTable, Tree

from ruff_sync.cli import Arguments
from ruff_sync.tui.app import RuffSyncApp

if TYPE_CHECKING:
    import pathlib

    from ruff_sync.tui.widgets import ConfigTree, RuleInspector

    from .conftest import CLIRunner


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
async def test_ruff_sync_app_mount_load_config_failure(
    mock_args: Arguments,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """on_mount should handle a failure to load the Ruff config gracefully."""

    # Force load_local_ruff_config to fail to exercise the error-handling path.
    def mock_fail(_: Any) -> Any:
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "ruff_sync.tui.app.load_local_ruff_config",
        mock_fail,
    )

    app = RuffSyncApp(mock_args)

    # Run the app so that on_mount is invoked.
    async with app.run_test() as pilot:
        # Let the app process startup/mount events.
        await pilot.pause()

        # When config loading fails, the app should keep the default (empty) config.
        assert app.config == {}
        tree = cast("ConfigTree", app.query_one("#config-tree"))
        assert not list(tree.root.children)


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
        assert tree.root.label is not None
        root_label = tree.root.label
        root_label_text = root_label.plain if hasattr(root_label, "plain") else root_label
        assert str(root_label_text) == "Local Configuration"
        # Check some children
        assert any(
            str(n.label.plain if hasattr(n.label, "plain") else n.label) == "line-length"
            for n in tree.root.children
        )
        assert any(
            str(n.label.plain if hasattr(n.label, "plain") else n.label) == "lint"
            for n in tree.root.children
        )


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
        node = next(
            n
            for n in tree.root.children
            if str(n.label.plain if hasattr(n.label, "plain") else n.label) == "line-length"
        )
        tree.select_node(node)
        await pilot.pause()

        table = app.query_one(DataTable)
        # For a simple value, CategoryTable.update_content(88) adds row ("Value", "88")
        assert table.row_count == 1
        row = table.get_row_at(0)
        assert [str(cell) for cell in row] == ["Value", "88"]


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
            lint_node = next(
                n
                for n in tree.root.children
                if str(n.label.plain if hasattr(n.label, "plain") else n.label) == "lint"
            )
            lint_node.expand()
            await pilot.pause()

            select_node = next(
                n
                for n in lint_node.children
                if str(n.label.plain if hasattr(n.label, "plain") else n.label) == "select"
            )
            select_node.expand()
            await pilot.pause()

            rule_node = next(
                n
                for n in select_node.children
                if str(n.label.plain if hasattr(n.label, "plain") else n.label) == "RUF012"
            )
            tree.select_node(rule_node)
            await pilot.pause()

            inspector = cast("RuleInspector", app.query_one("#inspector"))
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


def test_cli_inspect_subcommand(
    cli_run: CLIRunner, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that 'ruff-sync inspect' attempts to run the app."""
    # Mock load_local_ruff_config where it's used in RuffSyncApp.on_mount
    monkeypatch.setattr("ruff_sync.tui.app.load_local_ruff_config", lambda _: {})

    # Use patch to prevent the App from actually running (which would block/fail in CI)
    # and just verify it was instantiated and run() was called.
    with patch("ruff_sync.tui.app.RuffSyncApp.run", return_value=0) as mock_run:
        exit_code, _out, _err = cli_run(["inspect", "--to", str(tmp_path)])
        assert exit_code == 0
        mock_run.assert_called_once()


def test_cli_ruff_inspect_entry_point(
    cli_run: CLIRunner, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the 'ruff-inspect' entry point attempts to run the app."""
    # Mock load_local_ruff_config where it's used in RuffSyncApp.on_mount
    monkeypatch.setattr("ruff_sync.tui.app.load_local_ruff_config", lambda _: {})

    with patch("ruff_sync.tui.app.RuffSyncApp.run", return_value=0) as mock_run:
        # Program name 'ruff-inspect' should trigger the inspect logic
        exit_code, _out, _err = cli_run(["--to", str(tmp_path)], entry_point="ruff-inspect")
        assert exit_code == 0
        mock_run.assert_called_once()
