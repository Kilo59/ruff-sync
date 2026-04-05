"""TUI package for ruff-sync."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruff_sync.tui.app import RuffSyncApp


def get_tui_app() -> type[RuffSyncApp]:
    """Lazy-load the TUI and return the RuffSyncApp class.

    Returns:
        The RuffSyncApp class.

    Raises:
        SystemExit: If 'textual' is not installed or the TUI cannot be loaded.
    """
    from ruff_sync.dependencies import require_dependency  # noqa: PLC0415

    require_dependency("textual", extra_name="tui")

    from ruff_sync.tui.app import RuffSyncApp  # noqa: PLC0415

    return RuffSyncApp
