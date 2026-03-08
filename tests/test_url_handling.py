from __future__ import annotations

import pytest
from httpx import URL

from ruff_sync import github_url_to_raw_url


@pytest.mark.parametrize(
    "input_url, expected_url",
    [
        # Blob URLs
        (
            "https://github.com/pydantic/pydantic/blob/main/pyproject.toml",
            "https://raw.githubusercontent.com/pydantic/pydantic/main/pyproject.toml",
        ),
        (
            "https://github.com/org/repo/blob/develop/config/ruff.toml",
            "https://raw.githubusercontent.com/org/repo/develop/config/ruff.toml",
        ),
        # Repo URLs
        (
            "https://github.com/pydantic/pydantic",
            "https://raw.githubusercontent.com/pydantic/pydantic/main/pyproject.toml",
        ),
        (
            "https://github.com/Kilo59/ruff-sync/",
            "https://raw.githubusercontent.com/Kilo59/ruff-sync/main/pyproject.toml",
        ),
        # Non-GitHub URLs should be untouched
        (
            "https://example.com/pyproject.toml",
            "https://example.com/pyproject.toml",
        ),
        # Already raw URLs should be untouched (or at least valid)
        (
            "https://raw.githubusercontent.com/org/repo/main/pyproject.toml",
            "https://raw.githubusercontent.com/org/repo/main/pyproject.toml",
        ),
        # Unknown GitHub pattern
        (
            "https://github.com/org/repo/tree/main/subdir/pyproject.toml",
            "https://github.com/org/repo/tree/main/subdir/pyproject.toml",
        ),
        # False positive on substring in path
        (
            "https://notgithub.com/github.com/org/repo",
            "https://notgithub.com/github.com/org/repo",
        ),
        # www.github.com support
        (
            "https://www.github.com/pydantic/pydantic",
            "https://raw.githubusercontent.com/pydantic/pydantic/main/pyproject.toml",
        ),
    ],
)
def test_github_url_to_raw_url(input_url: str, expected_url: str):
    url = URL(input_url)
    result = github_url_to_raw_url(url)
    assert str(result) == expected_url
