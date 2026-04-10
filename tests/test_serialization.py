from __future__ import annotations

import logging
import pathlib

import pytest
import tomlkit
from httpx import URL

from ruff_sync.cli import Arguments
from ruff_sync.constants import DEFAULT_BRANCH, DEFAULT_EXCLUDE, MISSING
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


def test_serialize_ruff_sync_config_pre_commit_default_skipped():
    """When pre_commit is False (the default), the key must be absent from the serialized config."""
    doc = tomlkit.document()
    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=pathlib.Path(),
        exclude=DEFAULT_EXCLUDE,
        verbose=0,
        pre_commit=MISSING,
    )
    serialize_ruff_sync_config(doc, args)

    s = doc.as_string()
    assert "pre-commit-version-sync" not in s


def test_serialize_validate_and_strict_missing():
    doc = tomlkit.document()
    doc["tool"] = {"ruff-sync": {}}

    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=pathlib.Path(),
        exclude=DEFAULT_EXCLUDE,
        verbose=0,
        pre_commit=MISSING,
        validate=MISSING,
        strict=MISSING,
    )

    serialize_ruff_sync_config(doc, args)
    toml_str = tomlkit.dumps(doc)

    # When validate/strict are MISSING, they should not be persisted
    assert "validate" not in toml_str
    assert "strict" not in toml_str


def test_serialize_validate_and_strict_explicit():
    doc = tomlkit.document()
    doc["tool"] = {"ruff-sync": {}}

    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=pathlib.Path(),
        exclude=DEFAULT_EXCLUDE,
        verbose=0,
        pre_commit=MISSING,
        validate=True,
        strict=False,
    )

    serialize_ruff_sync_config(doc, args)
    toml_str = tomlkit.dumps(doc)

    # When validate/strict are explicitly provided, they should be persisted
    assert "validate = true" in toml_str
    assert "strict = false" in toml_str


def test_serialize_ruff_sync_config_exclude_deduplication():
    # Case: duplicates and extra entries -> written, deduped, first-occurrence order
    doc = tomlkit.document()
    exclude_with_duplicates = [
        "lint.per-file-ignores",
        "lint.ignore",
        "lint.ignore",
        "lint.extend-select",
    ]

    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=pathlib.Path(),
        exclude=exclude_with_duplicates,
        verbose=0,
    )

    serialize_ruff_sync_config(doc, args)

    ruff_sync_table = doc.get("tool", {}).get("ruff-sync", {})

    # Should be a single exclude array
    assert "exclude" in ruff_sync_table
    exclude_value = ruff_sync_table["exclude"]
    # tomlkit items might not be direct lists but behave like them
    assert list(exclude_value) == [
        "lint.per-file-ignores",
        "lint.ignore",
        "lint.extend-select",
    ]


def test_serialize_ruff_sync_config_preserves_existing():
    doc = tomlkit.document()
    tool = tomlkit.table()
    ruff_sync = tomlkit.table()
    ruff_sync.add("unrelated", "value")
    tool.add("ruff-sync", ruff_sync)
    doc.add("tool", tool)

    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=pathlib.Path(),
        exclude=DEFAULT_EXCLUDE,
        verbose=0,
    )

    serialize_ruff_sync_config(doc, args)

    s = doc.as_string()
    assert 'unrelated = "value"' in s
    assert 'upstream = "https://example.com/repo/pyproject.toml"' in s


def test_get_or_create_ruff_sync_table_non_table_tool():
    """If doc['tool'] exists but is not a Table it should be replaced, not appended."""
    from ruff_sync.core import _get_or_create_ruff_sync_table

    doc = tomlkit.document()
    doc.add("tool", tomlkit.items.String.from_raw("not-a-table"))  # Malformed: non-Table value

    table = _get_or_create_ruff_sync_table(doc)
    assert isinstance(table, tomlkit.items.Table)

    # Only one 'tool' key must exist (no duplicates)
    tool_keys = [k for k in doc if k == "tool"]
    assert len(tool_keys) == 1

    # The replacement table should contain the new ruff-sync sub-table
    assert isinstance(doc["tool"]["ruff-sync"], tomlkit.items.Table)  # type: ignore[index]


def test_get_or_create_ruff_sync_table_non_table_ruff_sync():
    """If tool['ruff-sync'] exists but is not a Table it should be replaced."""
    from ruff_sync.core import _get_or_create_ruff_sync_table

    doc = tomlkit.document()
    tool = tomlkit.table()
    tool.add("ruff-sync", 42)  # Malformed: non-Table value
    doc.add("tool", tool)

    table = _get_or_create_ruff_sync_table(doc)
    assert isinstance(table, tomlkit.items.Table)

    # Serialization should still succeed
    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=pathlib.Path(),
        exclude=DEFAULT_EXCLUDE,
        verbose=0,
    )
    from ruff_sync.core import serialize_ruff_sync_config

    serialize_ruff_sync_config(doc, args)
    s = doc.as_string()
    assert 'upstream = "https://example.com/repo/pyproject.toml"' in s


def test_serialize_ruff_sync_config_omits_defaults():
    doc = tomlkit.document()
    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=pathlib.Path(),
        exclude=DEFAULT_EXCLUDE,
        verbose=0,
        branch=DEFAULT_BRANCH,
        path=None,
        pre_commit=MISSING,
        save=True,
    )
    serialize_ruff_sync_config(doc, args)

    s = doc.as_string()
    assert "[tool.ruff-sync]" in s
    assert 'upstream = "https://example.com/repo/pyproject.toml"' in s
    assert "exclude" not in s
    assert "branch" not in s
    assert "path" not in s
    assert "pre-commit-version-sync" not in s


def test_serialize_ruff_sync_config_exclude_default_skipped():
    doc = tomlkit.document()
    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=pathlib.Path(),
        exclude=DEFAULT_EXCLUDE,
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
        exclude=DEFAULT_EXCLUDE,
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
        exclude=DEFAULT_EXCLUDE,
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
        exclude=DEFAULT_EXCLUDE,
        verbose=0,
    )
    serialize_ruff_sync_config(doc, args)

    s = doc.as_string()
    assert "upstream = [" in s
    assert '"https://example.com/repo1/pyproject.toml"' in s
    assert '"https://example.com/repo2/pyproject.toml"' in s


@pytest.mark.parametrize(
    "case",
    [
        # (init, save, pre_commit, expect_sync_pre_commit, expect_save)
        # MISSING now defaults to False for sync (preserving historical behavior)
        (True, None, MISSING, False, True),
        # explicit False disables sync
        (True, None, False, False, True),
        # save without init still writes [tool.ruff-sync] but does not init hooks
        (False, True, MISSING, False, True),
        # init with explicit --no-save should not serialize [tool.ruff-sync]
        (True, False, MISSING, False, False),
        # neither init nor save is truthy: no [tool.ruff-sync] section written
        (False, None, MISSING, False, False),
    ],
)
@pytest.mark.asyncio
async def test_pull_logging_and_serialization_triggers(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: pathlib.Path,
    case: tuple[bool, bool | None, bool, bool, bool],
) -> None:
    init, save, pre_commit, expect_sync_pre_commit, expect_save = case
    from ruff_sync import core

    # Mock _merge_multiple_upstreams to just return the doc unchanged
    async def mock_merge(doc, *args, **kwargs):
        return doc

    monkeypatch.setattr(core, "_merge_multiple_upstreams", mock_merge)

    # Track sync_pre_commit calls so we can verify the branching on pre_commit
    sync_calls: list[pathlib.Path] = []

    def mock_sync_pre_commit(path: pathlib.Path, dry_run: bool = False) -> bool:
        sync_calls.append(path)
        return True

    monkeypatch.setattr(core, "sync_pre_commit", mock_sync_pre_commit)

    target = tmp_path / "pyproject.toml"

    # When not using --init the file must already exist; pre-create it
    if not init:
        target.touch()

    # Ensure resolve_target_path returns our explicit file path so that pull()
    # does not treat the not-yet-existing target as a directory
    monkeypatch.setattr(core, "resolve_target_path", lambda to, up: to)

    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=target,
        exclude=["lint.per-file-ignores"],
        verbose=0,
        init=init,
        save=save,
        pre_commit=pre_commit,
    )

    with caplog.at_level(logging.INFO):
        await pull(args)

    contents = target.read_text()

    if expect_save:
        assert "[tool.ruff-sync]" in contents
        assert "upstream" in contents
    else:
        # when neither init nor save is truthy, no [tool.ruff-sync] section written
        assert "[tool.ruff-sync]" not in contents

    # sync_pre_commit is only called when pre_commit is explicitly True
    assert bool(sync_calls) is expect_sync_pre_commit


@pytest.mark.asyncio
async def test_pull_ruff_toml_skips_serialization(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: pathlib.Path,
    configure_logging: logging.Logger,
):
    """Serialization of [tool.ruff-sync] must be skipped when target is ruff.toml."""
    from ruff_sync import core

    async def mock_merge(doc, *args, **kwargs):
        return doc

    monkeypatch.setattr(core, "_merge_multiple_upstreams", mock_merge)

    target = tmp_path / "ruff.toml"
    # Ensure resolve_target_path returns our explicit file path
    monkeypatch.setattr(core, "resolve_target_path", lambda to, up: to)

    args = Arguments(
        command="pull",
        upstream=(URL("https://example.com/repo/pyproject.toml"),),
        to=target,
        exclude=["lint.per-file-ignores"],
        verbose=0,
        init=True,
        save=None,
    )

    with caplog.at_level(logging.INFO, logger="ruff_sync"):
        await pull(args)

    assert (
        "Skipping [tool.ruff-sync] configuration save because target is not pyproject.toml"
        in caplog.text
    )
    assert "tool" not in target.read_text()
    assert "ruff-sync" not in target.read_text()
