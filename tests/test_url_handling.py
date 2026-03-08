from __future__ import annotations

import pytest
from httpx import URL

from ruff_sync import resolve_raw_url


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
        # GitLab Repo URLs
        (
            "https://gitlab.com/gitlab-org/gitlab",
            "https://gitlab.com/gitlab-org/gitlab/-/raw/main/pyproject.toml",
        ),
        (
            "https://gitlab.com/gitlab-org/nested/group/sub-a/sub-b/project",
            "https://gitlab.com/gitlab-org/nested/group/sub-a/sub-b/project/-/raw/main/pyproject.toml",
        ),
        # GitLab Blob URLs
        (
            "https://gitlab.com/gitlab-org/gitlab/-/blob/master/pyproject.toml",
            "https://gitlab.com/gitlab-org/gitlab/-/raw/master/pyproject.toml",
        ),
        # GitLab other pattern (tree)
        (
            "https://gitlab.com/gitlab-org/gitlab/-/tree/master",
            "https://gitlab.com/gitlab-org/gitlab/-/tree/master",
        ),
    ],
)
def test_any_url_to_raw_url(input_url: str, expected_url: str):
    url = URL(input_url)
    result = resolve_raw_url(url)
    assert str(result) == expected_url


@pytest.mark.parametrize(
    "input_url, branch, path, expected_url",
    [
        (
            "https://github.com/org/repo",
            "develop",
            "libs/core",
            "https://raw.githubusercontent.com/org/repo/develop/libs/core/pyproject.toml",
        ),
        (
            "https://github.com/org/repo",
            "main",
            "",
            "https://raw.githubusercontent.com/org/repo/main/pyproject.toml",
        ),
        (
            "https://gitlab.com/org/repo",
            "v1.0",
            "config",
            "https://gitlab.com/org/repo/-/raw/v1.0/config/pyproject.toml",
        ),
    ],
)
def test_raw_url_with_branch_and_path(input_url: str, branch: str, path: str, expected_url: str):
    url = URL(input_url)
    result = resolve_raw_url(url, branch=branch, path=path)
    assert str(result) == expected_url
