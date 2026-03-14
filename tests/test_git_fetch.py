from __future__ import annotations

import pathlib
import subprocess

import pytest
from httpx import URL, AsyncClient

from ruff_sync import fetch_upstream_config, resolve_raw_url


@pytest.mark.asyncio
async def test_fetch_upstream_config_git(monkeypatch: pytest.MonkeyPatch):
    url = URL("git@github.com:Kilo59/ruff-sync.git")

    call_args_list = []

    def mock_run(cmd, **_kwargs):
        call_args_list.append(cmd)
        if cmd[1] == "clone":
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        elif cmd[3] == "restore":
            temp_dir = pathlib.Path(cmd[2])
            target_path = temp_dir / cmd[-1]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text("[tool.ruff]\nselect = ['E']")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    async with AsyncClient() as client:
        result, resolved_path = await fetch_upstream_config(url, client, branch="main", path="")

        assert result.read() == "[tool.ruff]\nselect = ['E']"
        assert resolved_path == "pyproject.toml"

        # Verify the subprocess arguments
        assert len(call_args_list) == 2
        clone_args = call_args_list[0]
        restore_args = call_args_list[1]

        # The last argument is the auto-generated temp_dir path
        assert clone_args[:-1] == [
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
        assert restore_args[:6] == [
            "git",
            "-C",
            clone_args[-1],
            "restore",
            "--source",
            "main",
        ]
        assert restore_args[6] == "pyproject.toml"


@pytest.mark.asyncio
async def test_fetch_upstream_config_git_with_path(monkeypatch: pytest.MonkeyPatch):
    url = URL("ssh://git@github.com/Kilo59/ruff-sync.git")

    call_args_list = []

    def mock_run(cmd, **_kwargs):
        call_args_list.append(cmd)
        if cmd[1] == "clone":
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        elif cmd[3] == "restore":
            temp_dir = pathlib.Path(cmd[2])
            target_path = temp_dir / cmd[-1]
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text("[tool.ruff]\nselect = ['F']")
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    async with AsyncClient() as client:
        result, resolved_path = await fetch_upstream_config(
            url, client, branch="main", path="sub/dir"
        )

        assert result.read() == "[tool.ruff]\nselect = ['F']"
        assert resolved_path == "sub/dir/pyproject.toml"

        assert len(call_args_list) == 2
        clone_args = call_args_list[0]
        restore_args = call_args_list[1]

        assert clone_args[:-1] == [
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
        assert restore_args[:6] == [
            "git",
            "-C",
            clone_args[-1],
            "restore",
            "--source",
            "main",
        ]
        assert restore_args[6] == "sub/dir/pyproject.toml"


@pytest.mark.asyncio
async def test_fetch_upstream_config_git_failure(monkeypatch: pytest.MonkeyPatch):
    url = URL("git@github.com:Kilo59/ruff-sync.git")

    def mock_run_fail(cmd, **_kwargs):
        raise subprocess.CalledProcessError(1, ["git", "clone"], stderr="Repository not found")

    monkeypatch.setattr(subprocess, "run", mock_run_fail)

    with pytest.raises(subprocess.CalledProcessError):
        async with AsyncClient() as client:
            await fetch_upstream_config(url, client, branch="main", path="")


@pytest.mark.asyncio
async def test_fetch_upstream_config_git_missing_file(monkeypatch: pytest.MonkeyPatch):
    url = URL("git@github.com:Kilo59/ruff-sync.git")

    def mock_run_success(cmd, **_kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run_success)

    with pytest.raises(FileNotFoundError, match="Configuration file not found in repository"):
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
