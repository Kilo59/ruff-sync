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
        assert app.theme == "amber-ember"

        # Check the actual theme object values (smoke test)
        # Verify high-contrast success color for Material Ghost
        theme = cast("Any", app.get_theme("material-ghost"))
        assert str(theme.success).upper() == "#2E7D32"
        assert str(theme.background).upper() == "#FAFAFA"


@pytest.mark.asyncio
async def test_theme_picker_cycling(mock_args: Arguments) -> None:
    """Test that pressing 't' cycles through all available themes and wraps around."""
    # Create mock config so on_mount doesn't fail
    pyproject = mock_args.to / "pyproject.toml"
    pyproject.write_text("[tool.ruff]\n", encoding="utf-8")

    app = RuffSyncApp(mock_args)

    async with app.run_test() as pilot:
        # Capture the initial theme name and its index in the registered themes.
        initial_theme_name = app.theme
        assert initial_theme_name in app.available_themes

        initial_index = list(app.available_themes).index(initial_theme_name)

        # Press "t" once and ensure we advanced to the next theme.
        await pilot.press("t")
        await pilot.pause()
        first_theme_name = app.theme
        first_index = list(app.available_themes).index(first_theme_name)

        assert first_index == (initial_index + 1) % len(app.available_themes)

        # Press "t" again and ensure we advanced one more step.
        await pilot.press("t")
        await pilot.pause()
        second_theme_name = app.theme
        second_index = list(app.available_themes).index(second_theme_name)

        assert second_index == (first_index + 1) % len(app.available_themes)

        # Now press "t" enough times to wrap all the way back to the initial theme.
        remaining_presses = (len(app.available_themes) - second_index + initial_index) % len(
            app.available_themes
        )
        for _ in range(remaining_presses):
            await pilot.press("t")
            await pilot.pause()

        assert app.theme == initial_theme_name
