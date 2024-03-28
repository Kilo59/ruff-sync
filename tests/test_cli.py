from __future__ import annotations

import subprocess

import pytest


def test_manpage():
    """Test that the manpage can be generated with ruff-sync --help with no errors."""
    completed = subprocess.run(  # noqa: PLW1510 # want to see the stdout/stderr
        ["ruff-sync", "--help"],
        capture_output=True,
        text=True,
    )
    print(completed.stdout)
    assert completed.returncode == 0, completed.stderr


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
