from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ruff_sync.cli import Arguments

if TYPE_CHECKING:
    import pathlib


@pytest.fixture
def mock_args(tmp_path: pathlib.Path) -> Arguments:
    """Fixture for mocking CLI arguments in TUI tests."""
    return Arguments(
        command="inspect",
        upstream=(),
        to=tmp_path,
        exclude=(),
        verbose=0,
    )
