from __future__ import annotations

import pathlib
import subprocess
from unittest.mock import patch  # noqa: TID251

import pytest
from httpx import URL, AsyncClient

from ruff_sync import fetch_upstream_config, resolve_raw_url


@pytest.mark.asyncio
async def test_fetch_upstream_config_git():
    url = URL("git@github.com:Kilo59/ruff-sync.git")

    with patch("ruff_sync.subprocess.run") as mock_run:
        # Mock what git clone does by writing to the temp directory
        def side_effect(cmd, **_kwargs):
            if cmd[1] == "clone":
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
            elif cmd[3] == "restore":
                temp_dir = pathlib.Path(cmd[2])
                target_path = temp_dir / cmd[-1]
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text("[tool.ruff]\nselect = ['E']")
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        async with AsyncClient() as client:
            result = await fetch_upstream_config(url, client, branch="main", path="")

        assert result.read() == "[tool.ruff]\nselect = ['E']"

        # Verify the subprocess arguments
        assert mock_run.call_count == 2
        clone_args, _ = mock_run.call_args_list[0]
        restore_args, _ = mock_run.call_args_list[1]

        # The last argument is the auto-generated temp_dir path
        assert clone_args[0][:-1] == [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--no-checkout",
            "--branch",
            "main",
            "git@github.com:Kilo59/ruff-sync.git",
        ]
        assert restore_args[0][:6] == [
            "git",
            "-C",
            clone_args[0][-1],
            "restore",
            "--source",
            "main",
        ]
        assert restore_args[0][6] == "pyproject.toml"


@pytest.mark.asyncio
async def test_fetch_upstream_config_git_with_path():
    url = URL("ssh://git@github.com/Kilo59/ruff-sync.git")

    with patch("ruff_sync.subprocess.run") as mock_run:

        def side_effect(cmd, **_kwargs):
            if cmd[1] == "clone":
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
            elif cmd[3] == "restore":
                temp_dir = pathlib.Path(cmd[2])
                target_path = temp_dir / cmd[-1]
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text("[tool.ruff]\nselect = ['F']")
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        mock_run.side_effect = side_effect

        async with AsyncClient() as client:
            result = await fetch_upstream_config(url, client, branch="main", path="sub/dir")

        assert result.read() == "[tool.ruff]\nselect = ['F']"

        assert mock_run.call_count == 2
        clone_args, _ = mock_run.call_args_list[0]
        restore_args, _ = mock_run.call_args_list[1]

        assert clone_args[0][:-1] == [
            "git",
            "clone",
            "--depth",
            "1",
            "--filter=blob:none",
            "--no-checkout",
            "--branch",
            "main",
            "ssh://git@github.com/Kilo59/ruff-sync.git",
        ]
        assert restore_args[0][:6] == [
            "git",
            "-C",
            clone_args[0][-1],
            "restore",
            "--source",
            "main",
        ]
        assert restore_args[0][6] == "sub/dir/pyproject.toml"


@pytest.mark.asyncio
async def test_fetch_upstream_config_git_failure():
    url = URL("git@github.com:Kilo59/ruff-sync.git")

    with patch("ruff_sync.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git", "clone"], stderr="Repository not found"
        )

        with pytest.raises(subprocess.CalledProcessError):
            async with AsyncClient() as client:
                await fetch_upstream_config(url, client, branch="main", path="")


def test_resolve_raw_url_git_ssh():
    url = URL("git@github.com:Kilo59/ruff-sync.git")
    resolved = resolve_raw_url(url)
    assert resolved == url

    url2 = URL("ssh://git@github.com/Kilo59/ruff-sync.git")
    resolved2 = resolve_raw_url(url2)
    assert resolved2 == url2

    url3 = URL("git+ssh://git@github.com/Kilo59/ruff-sync.git")
    resolved3 = resolve_raw_url(url3)
    assert resolved3 == url3
