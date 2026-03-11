from __future__ import annotations

import httpx
import pytest
from httpx import URL, AsyncClient

from ruff_sync import fetch_upstream_config, to_git_url


@pytest.mark.parametrize(
    "input_url, expected_git_url",
    [
        # GitHub Browser URLs
        (
            "https://github.com/pydantic/pydantic/blob/main/pyproject.toml",
            "git@github.com:pydantic/pydantic.git",
        ),
        (
            "https://github.com/org/repo/blob/develop/config/ruff.toml",
            "git@github.com:org/repo.git",
        ),
        # GitHub Repo URLs
        (
            "https://github.com/pydantic/pydantic",
            "git@github.com:pydantic/pydantic.git",
        ),
        # GitHub Raw URLs
        (
            "https://raw.githubusercontent.com/pydantic/pydantic/main/pyproject.toml",
            "git@github.com:pydantic/pydantic.git",
        ),
        # GitLab Repo URLs
        (
            "https://gitlab.com/gitlab-org/gitlab",
            "git@gitlab.com:gitlab-org/gitlab.git",
        ),
        (
            "https://gitlab.com/gitlab-org/nested/group/sub-a/sub-b/project",
            "git@gitlab.com:gitlab-org/nested/group/sub-a/sub-b/project.git",
        ),
        # GitLab Blob URLs
        (
            "https://gitlab.com/gitlab-org/gitlab/-/blob/master/pyproject.toml",
            "git@gitlab.com:gitlab-org/gitlab.git",
        ),
        # Already git URLs
        (
            "git@github.com:org/repo.git",
            "git@github.com:org/repo.git",
        ),
        # Non-matching URLs
        (
            "https://example.com/pyproject.toml",
            None,
        ),
    ],
)
def test_to_git_url(input_url: str, expected_git_url: str | None):
    url = URL(input_url)
    result = to_git_url(url)
    if expected_git_url is None:
        assert result is None
    else:
        assert str(result) == expected_git_url


@pytest.mark.asyncio
async def test_fetch_upstream_config_http_error_with_git_suggestion(monkeypatch):
    url = URL("https://github.com/org/repo/blob/main/pyproject.toml")

    async def mock_get(*args, **kwargs):
        # Create a mock response with 404 status
        request = httpx.Request("GET", url)
        response = httpx.Response(404, request=request)
        response.raise_for_status()

    # We need to mock the client's get method
    # Since fetch_upstream_config uses the client passed to it

    async with AsyncClient() as client:
        monkeypatch.setattr(client, "get", mock_get)

        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            await fetch_upstream_config(url, client, branch="main", path="")

        error_msg = str(excinfo.value)
        assert "HTTP error 404" in error_msg
        assert "git@github.com:org/repo.git" in error_msg
        assert "ruff-sync pull" in error_msg
