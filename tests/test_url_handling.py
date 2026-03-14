from __future__ import annotations

import httpx
import pytest
from httpx import URL, AsyncClient

from ruff_sync import fetch_upstream_config, is_ruff_toml_file, resolve_raw_url, to_git_url


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
        # Tree URLs (GitHub)
        (
            "https://github.com/Kilo59/ruff-sync/tree/main/configs/kitchen-sink",
            "https://raw.githubusercontent.com/Kilo59/ruff-sync/main/configs/kitchen-sink/pyproject.toml",
        ),
        (
            "https://github.com/org/repo/tree/develop/subdir",
            "https://raw.githubusercontent.com/org/repo/develop/subdir/pyproject.toml",
        ),
        # Tree URLs (GitHub)
        (
            "https://github.com/org/repo/tree/main/subdir/pyproject.toml",
            "https://raw.githubusercontent.com/org/repo/main/subdir/pyproject.toml",
        ),
        # Another unknown pattern
        (
            "https://github.com/org/repo/pull/123",
            "https://github.com/org/repo/pull/123",
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
            "https://gitlab.com/gitlab-org/gitlab/-/tree/master/subdir",
            "https://gitlab.com/gitlab-org/gitlab/-/raw/master/subdir/pyproject.toml",
        ),
        # GitLab other pattern (tree)
        (
            "https://gitlab.com/gitlab-org/gitlab/-/tree/master",
            "https://gitlab.com/gitlab-org/gitlab/-/raw/master/pyproject.toml",
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
async def test_fetch_upstream_config_with_ruff_toml_fallback(respx_mock):
    # Given a directory guess result that would normally point to pyproject.toml
    # If pyproject.toml does not exist but ruff.toml does, it should find ruff.toml
    base_url = "https://raw.githubusercontent.com/org/repo/main/configs"
    pyproject_url = f"{base_url}/pyproject.toml"
    ruff_url = f"{base_url}/ruff.toml"

    # Mock: ruff.toml exists, others don't
    respx_mock.get(ruff_url).mock(return_value=httpx.Response(200, text="line-length = 100"))
    respx_mock.get(f"{base_url}/.ruff.toml").mock(return_value=httpx.Response(404))
    respx_mock.get(pyproject_url).mock(return_value=httpx.Response(404))

    async with AsyncClient() as client:
        # The URL passed to fetch_upstream_config is usually the one resolved by resolve_raw_url
        url = URL(pyproject_url)
        result, resolved_url = await fetch_upstream_config(
            url, client, branch="main", path="configs"
        )
        assert result.read() == "line-length = 100"
        assert str(resolved_url) == ruff_url


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
