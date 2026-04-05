from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import patch

import pytest
from textual.widgets import DataTable, Tree

from ruff_sync.cli import Arguments
from ruff_sync.tui.app import RuffSyncApp
from ruff_sync.tui.screens import LegendScreen
from ruff_sync.tui.widgets import RuleInspector

if TYPE_CHECKING:
    import pathlib

    from ruff_sync.tui.widgets import ConfigTree

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
        # Root only has "Effective Rule Status" node
        assert len(tree.root.children) == 1
        label = tree.root.children[0].label
        label_text = label.plain if hasattr(label, "plain") else label
        assert str(label_text) == "Effective Rule Status"


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
            # Wait for background worker and tree repopulation (priming)
            while not app.effective_rules:
                await asyncio.sleep(0.1)
                await pilot.pause()

            tree = app.query_one(Tree)
            # Find and select RUF012 node in the now-stable tree
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
            tree.focus()
            tree.select_node(rule_node)
            await pilot.press("enter")

            inspector = app.query_one("#inspector", RuleInspector)
            # Wait for background worker and UI update
            for _ in range(20):
                await pilot.pause(0.2)
                if "RUF012" in str(inspector.source):
                    break

            # Verify Markdown content (simplified check)
            assert "RUF012" in str(inspector.source)


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


@pytest.mark.parametrize(
    "args, expected_command",
    [
        ([], "inspect"),
        (["--help"], "inspect"),
        (["check", "--to", "."], "check"),  # Should NOT be rewritten to 'inspect'
        (["--to", "."], "inspect"),  # Should be rewritten since '--to' is not a command
    ],
)
def test_cli_ruff_inspect_entry_point_variations(
    args: list[str],
    expected_command: str,
    cli_run: CLIRunner,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that the 'ruff-inspect' entry point correctly handles and rewrites arguments."""
    # Mock load_local_ruff_config where it's used in RuffSyncApp.on_mount
    monkeypatch.setattr("ruff_sync.tui.app.load_local_ruff_config", lambda _: {})

    # We need to simulate the program name 'ruff-inspect'
    # The 'to' arg is added to ensure we have a valid target if needed
    final_args = args
    if "--to" not in args and "--help" not in args:
        final_args = [*args, "--to", str(tmp_path)]

    # 1. Test running (using patched run() to avoid TUI execution)
    with patch("ruff_sync.tui.app.RuffSyncApp.run", return_value=0) as mock_run:
        exit_code, _out, _err = cli_run(final_args, entry_point="ruff-inspect")

        # If --help was passed, argparse will exit 0 and not call run()
        if "--help" in args:
            assert exit_code == 0
            mock_run.assert_not_called()
        elif expected_command == "inspect":
            assert exit_code == 0
            mock_run.assert_called_once()
        else:
            # For 'check', asyncio.run(check()) is called, not RuffSyncApp.run()
            assert exit_code == 0
            mock_run.assert_not_called()

    # 2. Test instantiation (to verify the command was correctly resolved)
    with (
        patch("ruff_sync.tui.app.RuffSyncApp.__init__", return_value=None) as mock_init,
        patch("ruff_sync.cli.asyncio.run", return_value=0),
        patch("ruff_sync.tui.app.RuffSyncApp.run", return_value=0),
    ):
        cli_run(final_args, entry_point="ruff-inspect")

        if "--help" not in args:
            if expected_command == "inspect":
                mock_init.assert_called_once()
                exec_args = mock_init.call_args[0][0]
                assert exec_args.command == "inspect"
            else:
                mock_init.assert_not_called()


@pytest.mark.asyncio
async def test_ruff_sync_app_show_legend(mock_args: Arguments) -> None:
    """The legend screen should be pushed when '?' is pressed."""
    app = RuffSyncApp(mock_args)
    async with app.run_test() as pilot:
        await pilot.press("?")
        await pilot.pause()
        assert isinstance(app.screen, LegendScreen)

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, LegendScreen)


@pytest.mark.asyncio
async def test_ruff_sync_app_copy_content(mock_args: Arguments) -> None:
    """The inspector content should be copied to the clipboard when 'c' is pressed."""
    app = RuffSyncApp(mock_args)
    # Mock copy_to_clipboard on the app instance
    with patch.object(RuffSyncApp, "copy_to_clipboard") as mock_copy:
        async with app.run_test() as pilot:
            # Manually update inspector to simulate a selected rule/config
            inspector = app.query_one(RuleInspector)
            inspector.update("Copied Content Test")
            await pilot.pause()

            await pilot.press("c")
            await pilot.pause()

            mock_copy.assert_called_once_with("Copied Content Test")


def test_require_dependency_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that require_dependency exits with code 1 if the package is missing."""
    from ruff_sync import dependencies as deps

    # Mock is_installed to return False
    monkeypatch.setattr(deps, "is_installed", lambda _: False)

    with pytest.raises(SystemExit) as excinfo:
        deps.require_dependency("nonexistent", "extra")

    assert excinfo.value.code == 1
