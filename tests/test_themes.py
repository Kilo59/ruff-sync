from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import pathlib

import pytest

from ruff_sync.cli import Arguments
from ruff_sync.tui.app import RuffSyncApp


@pytest.fixture
def mock_args(tmp_path: pathlib.Path) -> Arguments:
    return Arguments(
        command="inspect",
        upstream=(),
        to=tmp_path,
        exclude=(),
        verbose=0,
    )


@pytest.mark.asyncio
async def test_themes_registered(mock_args: Arguments) -> None:
    # Create mock config so on_mount doesn't fail
    pyproject = mock_args.to / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\n", encoding="utf-8")

    app = RuffSyncApp(mock_args)
    async with app.run_test():
        # Check that themes are registered
        assert "ruff-sync-slate" in app.available_themes
        assert "amber-ember" in app.available_themes
        assert "material-ghost" in app.available_themes

        # Check default theme
        assert app.theme == "ruff-sync-slate"

        # Check the actual theme object values (smoke test)
        # Use cast(Any, ...) for theme attributes as they may be complex
        theme = cast("Any", app.get_theme("ruff-sync-slate"))
        assert str(theme.primary).upper() == "#FFC107"
        assert str(theme.background).upper() == "#0F172A"


@pytest.mark.asyncio
async def test_theme_picker_binding(mock_args: Arguments) -> None:
    # Create mock config so on_mount doesn't fail
    pyproject = mock_args.to / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\n", encoding="utf-8")

    app = RuffSyncApp(mock_args)
    async with app.run_test():
        # Verify the 't' binding exists
        # In Textual, we can check bindings via app.bindings
        binding = next((b for b in app.BINDINGS if b[0] == "t"), None)
        assert binding is not None
        assert binding[1] == "change_theme"
