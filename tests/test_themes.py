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
        # Check that 'amber-ember' is registered and active
        assert "amber-ember" in app.available_themes
        assert app.theme == "amber-ember"

        # Check that removed custom themes are NOT there
        assert "ruff-sync-slate" not in app.available_themes
        assert "material-ghost" not in app.available_themes

        # Check the actual theme object values (smoke test)
        theme = cast("Any", app.get_theme("amber-ember"))
        assert str(theme.primary).upper() == "#FFB300"
        assert str(theme.background).upper() == "#121212"
