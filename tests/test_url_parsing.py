from __future__ import annotations

import pytest

from ruff_sync import is_ruff_toml_file


@pytest.mark.parametrize(
    "path_or_url,expected",
    [
        ("ruff.toml", True),
        (".ruff.toml", True),
        ("configs/ruff.toml", True),
        ("pyproject.toml", False),
        ("https://example.com/ruff.toml", True),
        ("https://example.com/ruff.toml?ref=main", True),
        ("https://example.com/ruff.toml#L10", True),
        ("https://example.com/path/to/ruff.toml?query=1#frag", True),
        ("https://example.com/pyproject.toml?file=ruff.toml", False),
        ("https://example.com/ruff.toml/other", False),
        # Case where it's not a URL but has query/fragment characters
        ("ruff.toml?raw=1", True),
        ("ruff.toml#section", True),
    ],
)
def test_is_ruff_toml_file(path_or_url: str, expected: bool):
    assert is_ruff_toml_file(path_or_url) is expected


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
