from __future__ import annotations

import logging
import pathlib

import pytest
import tomlkit
from httpx import URL

from ruff_sync.cli import Arguments
from ruff_sync.core import pull, serialize_ruff_sync_config


def test_serialize_ruff_sync_config_basic():
    doc = tomlkit.document()
    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=pathlib.Path(),
        exclude=["lint.per-file-ignores", "lint.ignore"],
        verbose=0,
        branch="develop",
        path="backend",
        semantic=False,
        diff=False,
        init=True,
        pre_commit=True,
        save=True,
    )
    serialize_ruff_sync_config(doc, args)

    s = doc.as_string()
    assert "[tool.ruff-sync]" in s
    assert 'upstream = "https://example.com/repo/pyproject.toml"' in s
    assert "exclude = [" in s
    assert '"lint.ignore"' in s
    assert 'branch = "develop"' in s
    assert 'path = "backend"' in s
    assert "pre-commit-version-sync = true" in s


def test_serialize_ruff_sync_config_exclude_default_skipped():
    doc = tomlkit.document()
    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=pathlib.Path(),
        exclude=["lint.per-file-ignores"],
        verbose=0,
    )
    serialize_ruff_sync_config(doc, args)

    s = doc.as_string()
    assert "[tool.ruff-sync]" in s
    assert "exclude" not in s


def test_serialize_ruff_sync_config_mixed_credentials(caplog: pytest.LogCaptureFixture):
    doc = tomlkit.document()
    args = Arguments(
        command="pull",
        upstream=(
            URL("https://example.com/repo/pyproject.toml"),
            URL("https://user:pass@example.com/repo/pyproject.toml"),
        ),
        to=pathlib.Path(),
        exclude=["lint.per-file-ignores"],
        verbose=0,
    )

    with caplog.at_level(logging.WARNING):
        serialize_ruff_sync_config(doc, args)

    s = doc.as_string()
    assert "[tool.ruff-sync]" not in s
    assert "Upstream URL contains credentials!" in caplog.text


def test_serialize_ruff_sync_config_skip_credentials(caplog: pytest.LogCaptureFixture):
    doc = tomlkit.document()
    args = Arguments(
        command="pull",
        upstream=(URL("https://user:pass@example.com/repo/pyproject.toml"),),
        to=pathlib.Path(),
        exclude=["lint.per-file-ignores"],
        verbose=0,
        branch="main",
        path="",
        init=True,
        save=True,
    )

    with caplog.at_level(logging.WARNING):
        serialize_ruff_sync_config(doc, args)

    s = doc.as_string()
    assert "[tool.ruff-sync]" not in s
    assert "Upstream URL contains credentials!" in caplog.text


def test_serialize_ruff_sync_config_multiple_upstreams():
    doc = tomlkit.document()
    args = Arguments(
        command="pull",
        upstream=(
            URL("https://example.com/repo1/pyproject.toml"),
            URL("https://example.com/repo2/pyproject.toml"),
        ),
        to=pathlib.Path(),
        exclude=["lint.per-file-ignores"],
        verbose=0,
    )
    serialize_ruff_sync_config(doc, args)

    s = doc.as_string()
    assert "upstream = [" in s
    assert '"https://example.com/repo1/pyproject.toml"' in s
    assert '"https://example.com/repo2/pyproject.toml"' in s


@pytest.mark.asyncio
async def test_pull_logging_and_serialization_triggers(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    from ruff_sync import core

    # Mock _merge_multiple_upstreams to just return the doc
    async def mock_merge(doc, *args, **kwargs):
        return doc

    monkeypatch.setattr(core, "_merge_multiple_upstreams", mock_merge)

    # Mock TOMLFile so we don't actually write to disk
    class MockTOMLFile:
        last_written_doc: tomlkit.TOMLDocument | None = None

        def __init__(self, path):
            self.path = path

        def read(self):
            return tomlkit.document()

        def write(self, doc):
            type(self).last_written_doc = doc

    monkeypatch.setattr(core, "TOMLFile", MockTOMLFile)
    monkeypatch.setattr(core, "resolve_target_path", lambda to, up: to)

    # Mock exists/touch/mkdir on Path to simulate --init
    monkeypatch.setattr("pathlib.Path.exists", lambda x: False)
    monkeypatch.setattr("pathlib.Path.touch", lambda x: None)
    monkeypatch.setattr("pathlib.Path.mkdir", lambda x, parents, exist_ok: None)

    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=pathlib.Path("pyproject.toml"),
        exclude=["lint.per-file-ignores"],
        verbose=0,
        init=True,
        save=None,  # should default to True because of init=True
    )

    with caplog.at_level(logging.INFO):
        await pull(args)

    assert "Saving [tool.ruff-sync] configuration to pyproject.toml" in caplog.text
    assert MockTOMLFile.last_written_doc is not None
    s = MockTOMLFile.last_written_doc.as_string()
    assert "[tool.ruff-sync]" in s
    assert 'upstream = "https://example.com/repo/pyproject.toml"' in s

    # Now test with ruff.toml
    caplog.clear()
    args = args._replace(to=pathlib.Path("ruff.toml"))

    with caplog.at_level(logging.INFO):
        await pull(args)

    assert (
        "Skipping [tool.ruff-sync] configuration save because target is not pyproject.toml"
        in caplog.text
    )

    # Now test --init --no-save
    caplog.clear()
    args = args._replace(to=pathlib.Path("pyproject.toml"), save=False)

    with caplog.at_level(logging.INFO):
        await pull(args)

    assert "Saving [tool.ruff-sync] configuration to pyproject.toml" not in caplog.text
