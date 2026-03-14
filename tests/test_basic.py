from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import pathlib
import shutil
import sys
from pprint import pformat as pf
from typing import TYPE_CHECKING, Any, Final, cast

import httpx
import pytest
import respx
import tomlkit
from httpx import URL
from pytest import param
from tomlkit import TOMLDocument
from tomlkit.items import Table
from tomlkit.toml_file import TOMLFile

import ruff_sync
import ruff_sync.cli as ruff_sync_cli

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

    from _pytest.mark.structures import ParameterSet
    from pyfakefs.fake_filesystem import FakeFilesystem

TEST_ROOT: Final = pathlib.Path(__file__).parent
PROJECT_ROOT: Final = TEST_ROOT.parent
ROOT_PYPROJECT_TOML_PATH: Final = PROJECT_ROOT / "pyproject.toml"
ROOT_PYPROJECT_TOML: Final = TOMLFile(ROOT_PYPROJECT_TOML_PATH)

SAMPLE_TOML_W_RUFF_SYNC_CFG: Final = TEST_ROOT / "w_ruff_sync_cfg"
SAMPLE_TOML_WITHOUT_RUFF_SYNC_CFG: Final = TEST_ROOT / "wo_ruff_sync_cfg"
SAMPLE_TOML_WITHOUT_RUFF_CFG: Final = TEST_ROOT / "wo_ruff_cfg"

TERMINAL_SIZE: Final[int] = shutil.get_terminal_size().columns


TOML_STRS_PARAMS: Final[Sequence[ParameterSet]] = [
    param(t.joinpath("pyproject.toml").read_text(), id=t.name)
    for t in (
        SAMPLE_TOML_W_RUFF_SYNC_CFG,
        SAMPLE_TOML_WITHOUT_RUFF_SYNC_CFG,
        SAMPLE_TOML_WITHOUT_RUFF_CFG,
    )
]


@pytest.fixture(scope="session")
def sep_str() -> str:
    return f"{'*' * TERMINAL_SIZE}"


@pytest.fixture(scope="session")
def pyproject_toml_s() -> str:
    """
    The contents of the root pyproject.toml file.
    Prevents problems with the file or file system being modified during tests.
    """
    s = ROOT_PYPROJECT_TOML_PATH.read_text()
    assert s, f"{ROOT_PYPROJECT_TOML_PATH} was empty"
    return s


@pytest.fixture
def toml_s() -> str:
    """A sample pyproject.toml file with ruff config."""
    return """[tool.ruff.lint]
target-version = "py38"
line-length = 120
lint.select = ["F", "ASYNC"]
lint.ignore = ["W191", "E111"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = [
    "F401", # unused import
    "F403", # star imports
]
"""


@pytest.mark.parametrize(
    "exclude", [("per-file-ignores", "line-length"), ("ignore", "target-version"), ()]
)
def test_toml_ruff_parse(toml_s: str, exclude: tuple[str, ...]):
    original_toml_doc = tomlkit.parse(toml_s)
    orginal_keys = set(cast("Any", original_toml_doc)["tool"]["ruff"]["lint"].keys())
    print(f"{pf(orginal_keys)}")

    parsed_toml_doc = ruff_sync.toml_ruff_parse(toml_s, exclude=exclude)
    print(f"\n{pf(parsed_toml_doc, compact=True)}")

    lint_config: TOMLDocument = parsed_toml_doc["lint"]  # type: ignore[assignment]

    for section in exclude:
        assert section not in lint_config

    expected_sections = orginal_keys - set(exclude)
    for section in expected_sections:
        assert section in cast("Any", original_toml_doc)["tool"]["ruff"]["lint"], (
            f"{section} was not in original doc, fix test"
        )

        assert section in lint_config, f"{section} was incorrectly excluded"


def test_apply_exclusions_top_level():
    """Top-level keys like target-version should be excluded directly."""
    full_toml = """\
[tool.ruff]
target-version = "py310"
line-length = 90
"""
    ruff_tbl = ruff_sync.get_ruff_tool_table(full_toml, exclude=["target-version"])
    assert "target-version" not in ruff_tbl
    assert "line-length" in ruff_tbl


def test_apply_exclusions_dotted_path():
    """Dotted paths like lint.per-file-ignores should walk into sub-tables."""
    full_toml = """\
[tool.ruff]
target-version = "py310"

[tool.ruff.lint]
select = ["F", "E"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"""
    ruff_tbl = ruff_sync.get_ruff_tool_table(full_toml, exclude=["lint.per-file-ignores"])
    assert "per-file-ignores" not in cast("Any", ruff_tbl)["lint"]
    # Other keys should be untouched
    assert cast("Any", ruff_tbl)["lint"]["select"] == ["F", "E"]
    assert ruff_tbl["target-version"] == "py310"


def test_apply_exclusions_missing_key_is_noop():
    """Excluding a key that doesn't exist should be a silent no-op."""
    full_toml = '[tool.ruff]\ntarget-version = "py310"\n'
    ruff_tbl = ruff_sync.get_ruff_tool_table(
        full_toml, exclude=["nonexistent", "lint.also-missing"]
    )
    assert ruff_tbl["target-version"] == "py310"


def test_apply_exclusions_mixed():
    """Mixing top-level and dotted paths in one exclude list."""
    full_toml = """\
[tool.ruff]
target-version = "py310"
line-length = 90

[tool.ruff.lint]
select = ["F"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"x.py" = ["F401"]
"""
    ruff_tbl = ruff_sync.get_ruff_tool_table(
        full_toml,
        exclude=["target-version", "lint.per-file-ignores", "lint.ignore"],
    )
    assert "target-version" not in ruff_tbl
    assert "line-length" in ruff_tbl
    assert "per-file-ignores" not in cast("Any", ruff_tbl)["lint"]
    assert cast("Any", ruff_tbl)["lint"]["select"] == ["F"]


def test_get_ruff_tool_table_with_dotted_exclude():
    """get_ruff_tool_table should pass dotted excludes through to _apply_exclusions."""
    full_toml = """\
[tool.ruff]
target-version = "py310"
line-length = 90

[tool.ruff.lint]
select = ["F"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"""
    ruff_tbl = ruff_sync.get_ruff_tool_table(
        full_toml,
        exclude=["line-length", "lint.per-file-ignores"],
    )
    assert isinstance(ruff_tbl, Table)
    assert "line-length" not in ruff_tbl
    assert "target-version" in ruff_tbl
    assert "per-file-ignores" not in cast("Any", ruff_tbl)["lint"]
    assert cast("Any", ruff_tbl)["lint"]["select"] == ["F"]


@pytest.mark.parametrize("toml_str", TOML_STRS_PARAMS)
def test_get_ruff_tool_table(toml_str: str):
    """
    Test the get_ruff_tool_table() returns a tool.ruff table regardless of if the
    input has one or not.
    """
    ruff_table = ruff_sync.get_ruff_tool_table(toml_str)
    print(type(ruff_table))
    print(f"Ruff Table:\n{ruff_table.as_string()}")
    assert isinstance(ruff_table, Table)


@pytest.mark.parametrize(
    "source",
    [
        param(
            SAMPLE_TOML_WITHOUT_RUFF_CFG.joinpath("pyproject.toml").read_text(),
            id="no ruff cfg",
        ),
        param(
            SAMPLE_TOML_WITHOUT_RUFF_SYNC_CFG.joinpath("pyproject.toml").read_text(),
            id="no sync cfg",
        ),
    ],
)
def test_merge_ruff_toml(source: str, toml_s: str, sep_str: str):
    upstream_toml: str = toml_s
    print(f"Source\n{sep_str}\n{source}\n")
    print(f"Upstream\n{sep_str}\n{upstream_toml}")

    source_toml = tomlkit.parse(source)
    upstream_ruff: Table = tomlkit.parse(upstream_toml)["tool"]["ruff"]  # type: ignore[index,assignment]

    merged_ruff = ruff_sync.merge_ruff_toml(source_toml, upstream_ruff_doc=upstream_ruff)
    print(f"Merged\n{sep_str}\n{merged_ruff.as_string()}\n")

    source_ruff = source_toml.get("tool", {}).get("ruff")
    for key in upstream_ruff:
        assert key in source_ruff, f"{key} was not in the updated source ruff config"


@pytest.fixture
def mock_http(toml_s: str) -> Generator[respx.MockRouter, None, None]:
    with respx.mock(base_url="https://example.com/") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=toml_s,
        )
        yield respx_mock


@pytest.fixture
def fake_fs_source(fs: FakeFilesystem, pyproject_toml_s: str) -> pathlib.Path:
    """Create a fake file system with a pyproject.toml file."""
    ff = fs.create_file("my_dir/pyproject.toml", contents=pyproject_toml_s)
    ff_path = pathlib.Path(ff.path)  # type: ignore[arg-type]
    assert ff_path.read_text() == pyproject_toml_s
    return ff_path


@pytest.mark.xfail
@pytest.mark.asyncio
async def test_sync_updates_ruff_config(
    mock_http: respx.MockRouter, fake_fs_source: pathlib.Path, sep_str: str
):
    original_toml = fake_fs_source.read_text()
    original_ruff_config: Table = tomlkit.parse(original_toml)["tool"]["ruff"]  # type: ignore[index,assignment]
    print(f"Original tool.ruff:\n{sep_str}\n{tomlkit.dumps(original_ruff_config)}\n")

    upstream = URL("https://example.com/pyproject.toml")
    upstream_toml = httpx.get(upstream).text  # blocking but doesn't matter
    await ruff_sync.pull(
        ruff_sync.Arguments(
            command="pull",
            upstream=upstream,
            to=fake_fs_source,
            exclude=(),
            verbose=0,
        )
    )
    updated_toml = fake_fs_source.read_text()
    updated_ruff_config: Table = tomlkit.parse(updated_toml)["tool"]["ruff"]  # type: ignore[index,assignment]
    print(f"\nUpdated tool.ruff\n{sep_str}\n{tomlkit.dumps(updated_ruff_config)}")
    assert original_toml != updated_toml

    assert set(original_ruff_config.keys()).issubset(set(updated_ruff_config.keys()))

    # Ensure the updated ruff config has the same keys as the original
    for key in original_ruff_config:
        assert key in updated_ruff_config, f"Original key {key} was not in updated ruff config"

    # Ensure the updated ruff config has the expected updated values from upstream
    upstream_ruff_config: Table = tomlkit.parse(upstream_toml)["tool"]["ruff"]  # type: ignore[index,assignment]
    print("Upstream updates...")
    for key, value in upstream_ruff_config.items():
        print(f"  {key}", end=" ")
        assert updated_ruff_config[key] == value, f"{key} was not updated"
        print("✅")


@contextlib.contextmanager
def temp_cd(path: pathlib.Path) -> Generator[pathlib.Path, None, None]:
    """Context manager to temporarily change the working directory."""
    old_dir = pathlib.Path.cwd()
    os.chdir(path)
    try:
        yield pathlib.Path.cwd()
    finally:
        os.chdir(old_dir)


@pytest.mark.filterwarnings("ignore:Unknown ruff-sync configuration")
@pytest.mark.parametrize(
    ["sample_toml_dir", "expected_config"],
    [
        param(
            SAMPLE_TOML_W_RUFF_SYNC_CFG,
            {
                "upstream": "https://raw.githubusercontent.com/pydantic/pydantic/main/pyproject.toml",
                "exclude": ["per-file-ignores", "ignore", "line-length"],
            },
            id=SAMPLE_TOML_W_RUFF_SYNC_CFG.name,
        ),
        param(
            SAMPLE_TOML_WITHOUT_RUFF_CFG,
            {
                "upstream": "https://raw.githubusercontent.com/pydantic/pydantic/main/pyproject.toml",
                "exclude": ["per-file-ignores", "ignore", "line-length"],
            },
            id=SAMPLE_TOML_WITHOUT_RUFF_CFG.name,
        ),
        param(
            SAMPLE_TOML_WITHOUT_RUFF_SYNC_CFG,
            {},
            id=SAMPLE_TOML_WITHOUT_RUFF_SYNC_CFG.name,
        ),
    ],
)
def test_loading_ruff_sync_config(
    sample_toml_dir: pathlib.Path, expected_config: dict[str, list[str] | str]
):
    """Test that that the ruff_sync settings are loaded from the pyproject.toml."""
    sample_pyproject_toml = sample_toml_dir / "pyproject.toml"
    assert sample_pyproject_toml.exists(), f"{sample_pyproject_toml} does not exist"

    config = ruff_sync.get_config(sample_toml_dir)
    print(f"Config:\n{pf(config)}")
    assert expected_config == config


def test_exclude_resolution_cli_precedence(monkeypatch: pytest.MonkeyPatch):
    """CLI exclude should override all others."""
    captured_args: list[ruff_sync.Arguments] = []

    async def mock_sync(args: ruff_sync.Arguments) -> Any:
        captured_args.append(args)
        await asyncio.sleep(0)

    monkeypatch.setattr(sys, "argv", ["ruff-sync", "http://example.com", "--exclude", "from-cli"])
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {"exclude": ["from-config"]})
    monkeypatch.setattr(ruff_sync_cli, "pull", mock_sync)

    ruff_sync.main()

    assert len(captured_args) == 1
    assert captured_args[0].exclude == ["from-cli"]


def test_exclude_resolution_config_precedence(monkeypatch: pytest.MonkeyPatch):
    """[tool.ruff-sync] exclude should override default."""
    captured_args: list[ruff_sync.Arguments] = []

    async def mock_sync(args: ruff_sync.Arguments) -> Any:
        captured_args.append(args)
        await asyncio.sleep(0)

    monkeypatch.setattr(sys, "argv", ["ruff-sync", "http://example.com"])
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {"exclude": ["from-config"]})
    monkeypatch.setattr(ruff_sync_cli, "pull", mock_sync)

    ruff_sync.main()

    assert len(captured_args) == 1
    assert captured_args[0].exclude == ["from-config"]


def test_exclude_resolution_default(monkeypatch: pytest.MonkeyPatch):
    """Default exclude should apply when neither CLI nor Config provides it."""
    captured_args: list[ruff_sync.Arguments] = []

    async def mock_sync(args: ruff_sync.Arguments) -> Any:
        captured_args.append(args)
        await asyncio.sleep(0)

    monkeypatch.setattr(sys, "argv", ["ruff-sync", "http://example.com"])
    # Mock get_config to return a config without 'exclude' (use defaults)
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {})
    monkeypatch.setattr(ruff_sync_cli, "pull", mock_sync)

    ruff_sync.main()

    assert len(captured_args) == 1
    assert set(captured_args[0].exclude) == ruff_sync_cli._DEFAULT_EXCLUDE


def test_main_default_to_resolution(monkeypatch: pytest.MonkeyPatch):
    """Verify that main() resolves 'to' as a Path object by default."""
    captured_args: list[ruff_sync.Arguments] = []

    async def mock_sync(args: ruff_sync.Arguments) -> Any:
        captured_args.append(args)
        await asyncio.sleep(0)

    # No --to, --source, or even upstream (we'll mock config to provide upstream)
    monkeypatch.setattr(sys, "argv", ["ruff-sync"])
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {"upstream": "http://example.com"})
    monkeypatch.setattr(ruff_sync_cli, "pull", mock_sync)

    ruff_sync.main()

    assert len(captured_args) == 1
    # This specifically checks that it's a Path object, not a string
    assert isinstance(captured_args[0].to, pathlib.Path)
    # And that it represents the current directory
    assert str(captured_args[0].to) == "."


def test_upstream_resolution_cli_precedence(monkeypatch: pytest.MonkeyPatch):
    """CLI upstream should override config."""
    captured_args: list[ruff_sync.Arguments] = []

    async def mock_sync(args: ruff_sync.Arguments) -> Any:
        captured_args.append(args)
        await asyncio.sleep(0)

    monkeypatch.setattr(sys, "argv", ["ruff-sync", "http://cli.com"])
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {"upstream": "http://config.com"})
    monkeypatch.setattr(ruff_sync_cli, "pull", mock_sync)

    ruff_sync.main()

    assert len(captured_args) == 1
    assert str(captured_args[0].upstream) == "http://cli.com"


def test_upstream_resolution_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Error when no upstream is provided via CLI or config."""
    captured_args: list[ruff_sync.Arguments] = []

    async def mock_sync(args: ruff_sync.Arguments) -> Any:
        captured_args.append(args)
        await asyncio.sleep(0)

    # No CLI upstream argument
    monkeypatch.setattr(sys, "argv", ["ruff-sync"])
    # No upstream in config
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {})
    # Ensure sync is never called if upstream is missing
    monkeypatch.setattr(ruff_sync_cli, "pull", mock_sync)

    with pytest.raises(SystemExit) as excinfo:
        ruff_sync.main()

    # Non-zero exit code on failure
    assert excinfo.value.code != 0

    captured = capsys.readouterr()
    # Error message should indicate that an upstream is required
    assert "upstream" in captured.err
    assert "[tool.ruff-sync]" in captured.err

    # When erroring early, sync must not be invoked
    assert captured_args == []


def test_upstream_resolution_config_precedence(monkeypatch: pytest.MonkeyPatch):
    """[tool.ruff-sync] upstream should be used if CLI one is missing."""
    captured_args: list[ruff_sync.Arguments] = []

    async def mock_sync(args: ruff_sync.Arguments) -> Any:
        captured_args.append(args)
        await asyncio.sleep(0)

    monkeypatch.setattr(sys, "argv", ["ruff-sync"])
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {"upstream": "http://config.com"})
    monkeypatch.setattr(ruff_sync_cli, "pull", mock_sync)

    ruff_sync.main()

    assert len(captured_args) == 1
    assert str(captured_args[0].upstream) == "http://config.com"


@pytest.mark.parametrize(
    ["verbose_count", "expected_level"],
    [
        (0, logging.WARNING),
        (1, logging.INFO),
        (2, logging.DEBUG),
        (3, logging.DEBUG),
    ],
)
def test_verbosity_log_level(
    monkeypatch: pytest.MonkeyPatch, verbose_count: int, expected_level: int
):
    """Test that the log level is correctly set based on the verbose count."""
    captured_args: list[ruff_sync.Arguments] = []

    def mock_sync(args: ruff_sync.Arguments) -> Any:
        captured_args.append(args)
        return asyncio.sleep(0)

    argv = ["ruff-sync", "http://example.com"]
    if verbose_count > 0:
        argv.append(f"-{'v' * verbose_count}")

    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {})
    monkeypatch.setattr(ruff_sync_cli, "pull", mock_sync)

    # Reset LOGGER state before test
    monkeypatch.setattr(ruff_sync_cli.LOGGER, "level", logging.NOTSET)
    monkeypatch.setattr(ruff_sync_cli.LOGGER, "handlers", [])

    ruff_sync.main()

    # Verify that the computed log level matches what we expect for this verbosity
    assert ruff_sync_cli.LOGGER.level == expected_level

    # Verify that the verbose flag value propagates into Arguments.verbose
    assert len(captured_args) == 1
    assert captured_args[0].verbose == verbose_count


@pytest.mark.asyncio
async def test_sync_default_exclude(fs: FakeFilesystem):
    """Integration style test for default exclude functionality."""
    source_toml = """[tool.ruff]
target-version = "py310"
"""
    upstream_toml = """[tool.ruff]
target-version = "py311"
[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
"""
    ff = fs.create_file("pyproject.toml", contents=source_toml)
    ff_path = pathlib.Path(ff.path)  # type: ignore[arg-type]

    with respx.mock(base_url="https://example.com/") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_toml,
        )
        await ruff_sync.pull(
            ruff_sync.Arguments(
                command="pull",
                upstream=URL("https://example.com/pyproject.toml"),
                to=ff_path,
                exclude=ruff_sync_cli._DEFAULT_EXCLUDE,
                verbose=0,
            )
        )

    updated_toml = ff_path.read_text()
    assert 'target-version = "py311"' in updated_toml
    assert "per-file-ignores" not in updated_toml


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
