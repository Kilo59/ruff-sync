from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import pathlib
import shutil
import sys
from pprint import pformat as pf
from typing import TYPE_CHECKING, Any, Final, NamedTuple, cast

import httpx
import pytest
import respx
import tomlkit
from httpx import URL
from pytest import param
from tomlkit import TOMLDocument, document
from tomlkit.items import Table
from tomlkit.toml_file import TOMLFile

import ruff_sync
import ruff_sync.cli as ruff_sync_cli
from ruff_sync.constants import DEFAULT_EXCLUDE, MISSING
from ruff_sync.core import (
    UpstreamError,
    _merge_multiple_upstreams,
    fetch_upstreams_concurrently,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Sequence

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


class CLIPatch(NamedTuple):
    """Container for CLI patch data."""

    captured_args: list[ruff_sync.Arguments]
    errors: list[str]
    set_config: Callable[[dict[str, Any]], None]


@pytest.fixture
def patch_cli(monkeypatch: pytest.MonkeyPatch) -> CLIPatch:
    """Fixture to patch CLI components and capture arguments/errors."""
    captured_args: list[ruff_sync.Arguments] = []
    errors: list[str] = []

    async def mock_sync(args: ruff_sync.Arguments) -> Any:
        captured_args.append(args)
        await asyncio.sleep(0)

    def fake_error(message: str) -> None:
        errors.append(message)
        raise SystemExit(2)

    def set_config(config: dict[str, Any]) -> None:
        monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: config)

    monkeypatch.setattr(ruff_sync_cli, "pull", mock_sync)
    monkeypatch.setattr(ruff_sync_cli, "check", mock_sync)
    monkeypatch.setattr(ruff_sync_cli.PARSER, "error", fake_error)

    return CLIPatch(captured_args, errors, set_config)


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
            upstream=(upstream,),
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


def test_exclude_resolution_cli_precedence(patch_cli: CLIPatch):
    """CLI exclude should override all others."""
    sys.argv = ["ruff-sync", "http://example.com", "--exclude", "from-cli"]
    patch_cli.set_config({"exclude": ["from-config"]})

    ruff_sync.main()

    assert len(patch_cli.captured_args) == 1
    assert patch_cli.captured_args[0].exclude == ["from-cli"]


def test_exclude_resolution_config_precedence(patch_cli: CLIPatch):
    """[tool.ruff-sync] exclude should override default."""
    sys.argv = ["ruff-sync", "http://example.com"]
    patch_cli.set_config({"exclude": ["from-config"]})

    ruff_sync.main()

    assert len(patch_cli.captured_args) == 1
    assert patch_cli.captured_args[0].exclude == ["from-config"]


def test_exclude_resolution_default_is_missing(patch_cli: CLIPatch):
    """Default exclude should be MISSING when neither CLI nor config provides it.

    The CLI leaves `exclude` as MISSING so that downstream resolution (in
    `_merge_multiple_upstreams`) applies the correct DEFAULT_EXCLUDE set.
    """
    sys.argv = ["ruff-sync", "http://example.com"]
    # Mock get_config to return a config without 'exclude' (use defaults)
    patch_cli.set_config({})

    ruff_sync.main()

    assert len(patch_cli.captured_args) == 1
    # The CLI should leave `exclude` as MISSING so that default resolution is applied later.
    exclude = patch_cli.captured_args[0].exclude
    assert exclude is MISSING

    # Simulate downstream default resolution to ensure the default exclude set is used.
    resolved_exclude = DEFAULT_EXCLUDE if exclude is MISSING else exclude
    assert set(resolved_exclude) == DEFAULT_EXCLUDE


def test_main_default_to_resolution(patch_cli: CLIPatch):
    """Verify that main() resolves 'to' as a Path object by default."""
    # No --to, --source, or even upstream (we'll mock config to provide upstream)
    sys.argv = ["ruff-sync"]
    patch_cli.set_config({"upstream": "http://example.com"})

    ruff_sync.main()

    assert len(patch_cli.captured_args) == 1
    # This specifically checks that it's a Path object, not a string
    assert isinstance(patch_cli.captured_args[0].to, pathlib.Path)
    # And that it represents the current directory
    assert str(patch_cli.captured_args[0].to) == "."


def test_upstream_resolution_cli_precedence(patch_cli: CLIPatch):
    """CLI upstream should override config."""
    sys.argv = ["ruff-sync", "http://cli.com"]
    patch_cli.set_config({"upstream": "http://config.com"})

    ruff_sync.main()

    assert len(patch_cli.captured_args) == 1
    assert str(patch_cli.captured_args[0].upstream[0]) == "http://cli.com"


def test_upstream_resolution_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Error when no upstream is provided via CLI or config."""


def test_upstream_required(patch_cli: CLIPatch):
    """If no upstream is provided, ruff-sync should error and exit."""
    # No CLI upstream argument
    sys.argv = ["ruff-sync"]
    # No upstream in config
    patch_cli.set_config({})

    with pytest.raises(SystemExit) as excinfo:
        ruff_sync.main()

    # Non-zero exit code on failure
    assert excinfo.value.code != 0

    # Error message should indicate that an upstream is required
    assert patch_cli.errors, "PARSER.error should be called when upstream is missing"
    assert "upstream" in patch_cli.errors[0]
    assert "[tool.ruff-sync]" in patch_cli.errors[0]

    # When erroring early, sync must not be invoked
    assert patch_cli.captured_args == []


def test_upstream_resolution_config_precedence(patch_cli: CLIPatch):
    """[tool.ruff-sync] upstream should be used if CLI one is missing."""
    sys.argv = ["ruff-sync"]
    patch_cli.set_config({"upstream": "http://config.com"})

    ruff_sync.main()

    assert len(patch_cli.captured_args) == 1
    assert str(patch_cli.captured_args[0].upstream[0]) == "http://config.com"


def test_upstream_resolution_multiple_cli(patch_cli: CLIPatch):
    """Multiple CLI upstreams should be returned as a tuple."""
    sys.argv = ["ruff-sync", "http://u1.com", "http://u2.com"]
    patch_cli.set_config({})

    ruff_sync.main()

    assert len(patch_cli.captured_args) == 1
    assert patch_cli.captured_args[0].upstream == (URL("http://u1.com"), URL("http://u2.com"))


def test_upstream_resolution_multiple_config(patch_cli: CLIPatch):
    """Multiple upstreams in config should be returned as a tuple."""
    sys.argv = ["ruff-sync"]
    patch_cli.set_config({"upstream": ["http://u1.com", "http://u2.com"]})

    ruff_sync.main()

    assert len(patch_cli.captured_args) == 1
    assert patch_cli.captured_args[0].upstream == (URL("http://u1.com"), URL("http://u2.com"))


def test_upstream_resolution_cli_precedence_over_config(patch_cli: CLIPatch) -> None:
    """CLI upstreams should override any upstreams defined in config."""
    # Both CLI and config specify upstreams; CLI should win.
    sys.argv = ["ruff-sync", "http://cli.com"]
    patch_cli.set_config({"upstream": ["http://config.com"]})

    ruff_sync.main()

    assert len(patch_cli.captured_args) == 1
    assert patch_cli.captured_args[0].upstream == (URL("http://cli.com"),)


@pytest.mark.parametrize(
    "bad_upstream",
    [
        42,
        {"url": "http://example.com"},
        ["http://ok.com", 123],
    ],
)
def test_upstream_resolution_invalid_config_types(
    patch_cli: CLIPatch,
    bad_upstream: Any,
) -> None:
    """Invalid `upstream` types in config should trigger PARSER.error."""
    sys.argv = ["ruff-sync"]  # no CLI upstreams
    patch_cli.set_config({"upstream": bad_upstream})

    with pytest.raises(SystemExit):
        ruff_sync.main()

    assert patch_cli.errors, "PARSER.error should be called for invalid upstream types"
    assert (
        "string or a list of strings" in patch_cli.errors[0]
        or "must be strings" in patch_cli.errors[0]
    )


def test_upstream_resolution_empty_list_in_config(patch_cli: CLIPatch) -> None:
    """An empty upstream list in config should be treated as an error."""
    sys.argv = ["ruff-sync"]  # no CLI upstreams
    patch_cli.set_config({"upstream": []})

    with pytest.raises(SystemExit):
        ruff_sync.main()

    assert patch_cli.errors, "PARSER.error should be called when no upstreams are resolved"
    assert "cannot be empty" in patch_cli.errors[0]


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
    monkeypatch: pytest.MonkeyPatch,
    patch_cli: CLIPatch,
    verbose_count: int,
    expected_level: int,
):
    """Test that the log level is correctly set based on the verbose count."""
    argv = ["ruff-sync", "http://example.com"]
    if verbose_count > 0:
        argv.append(f"-{'v' * verbose_count}")

    sys.argv = argv
    patch_cli.set_config({})

    # Reset LOGGER state before test
    monkeypatch.setattr(ruff_sync_cli.LOGGER, "level", logging.NOTSET)
    monkeypatch.setattr(ruff_sync_cli.LOGGER, "handlers", [])

    ruff_sync.main()

    # Verify that the computed log level matches what we expect for this verbosity
    assert ruff_sync_cli.LOGGER.getEffectiveLevel() == expected_level

    # Verify that the verbose flag value propagates into Arguments.verbose
    assert len(patch_cli.captured_args) == 1
    assert patch_cli.captured_args[0].verbose == verbose_count


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
                upstream=(URL("https://example.com/pyproject.toml"),),
                to=ff_path,
                exclude=DEFAULT_EXCLUDE,
                verbose=0,
            )
        )

    updated_toml = ff_path.read_text()
    assert 'target-version = "py311"' in updated_toml
    assert "per-file-ignores" not in updated_toml


def test_ruff_config_file_name_tried_order() -> None:
    """Test that tried_order returns the expected sequence of filenames."""
    order = ruff_sync.RuffConfigFileName.tried_order()
    assert order == [
        ruff_sync.RuffConfigFileName.RUFF_TOML,
        ruff_sync.RuffConfigFileName.DOT_RUFF_TOML,
        ruff_sync.RuffConfigFileName.PYPROJECT_TOML,
    ]


def test_ruff_config_file_name_str() -> None:
    """Test that string conversion returns the literal filename."""
    assert str(ruff_sync.RuffConfigFileName.PYPROJECT_TOML) == "pyproject.toml"
    assert str(ruff_sync.RuffConfigFileName.RUFF_TOML) == "ruff.toml"
    assert str(ruff_sync.RuffConfigFileName.DOT_RUFF_TOML) == ".ruff.toml"


def test_ruff_config_file_name_path_join() -> None:
    """Test that the Enum members can be used directly in path joining."""
    path = pathlib.Path("base/path")
    # Path / Enum works because it's a str mixin
    assert path / ruff_sync.RuffConfigFileName.PYPROJECT_TOML == pathlib.Path(
        "base/path/pyproject.toml"
    )
    assert path / ruff_sync.RuffConfigFileName.RUFF_TOML == pathlib.Path("base/path/ruff.toml")
    assert path / ruff_sync.RuffConfigFileName.DOT_RUFF_TOML == pathlib.Path("base/path/.ruff.toml")


def test_ruff_config_file_name_equality() -> None:
    """Test equality comparisons."""
    # intentional non-overlapping comparison
    assert ruff_sync.RuffConfigFileName.PYPROJECT_TOML == "pyproject.toml"  # type: ignore[comparison-overlap]
    assert ruff_sync.RuffConfigFileName.RUFF_TOML == "ruff.toml"
    assert ruff_sync.RuffConfigFileName.DOT_RUFF_TOML == ".ruff.toml"
    assert ruff_sync.RuffConfigFileName.PYPROJECT_TOML != ruff_sync.RuffConfigFileName.RUFF_TOML


@pytest.mark.asyncio
async def test_merge_multiple_upstreams_preserves_order(respx_mock: respx.Router):
    """Verify that multiple upstreams are merged in the given order."""
    # Setup mock data
    target_doc = document()

    args = ruff_sync.Arguments(
        command="pull",
        upstream=(URL("http://one.toml"), URL("http://two.toml")),
        to=pathlib.Path(),
        exclude=[],
        verbose=0,
        branch="main",
        path="",
    )

    # Mock HTTP responses using respx
    respx_mock.get("http://one.toml").return_value = httpx.Response(
        200, text="[tool.ruff]\nline-length = 80"
    )
    respx_mock.get("http://two.toml").return_value = httpx.Response(
        200, text="[tool.ruff]\nline-length = 100"
    )

    async with httpx.AsyncClient() as client:
        result_doc = await _merge_multiple_upstreams(target_doc, False, args, client)

        # Verify both URLs were fetched
        assert respx_mock.get("http://one.toml").called
        assert respx_mock.get("http://two.toml").called

        # Verify the sequential merge result (the last one wins for specific keys)
        ruff_config = result_doc.get("tool", {}).get("ruff", {})
        assert ruff_config.get("line-length") == 100


@pytest.mark.asyncio
async def test_fetch_upstreams_concurrently_verified(respx_mock: respx.Router):
    """Verify that fetch_upstreams_concurrently actually runs tasks in parallel."""
    events = []

    async def side_effect_one(request: httpx.Request) -> httpx.Response:
        events.append("start_one")
        await asyncio.sleep(0.05)
        events.append("end_one")
        return httpx.Response(200, text="[tool.ruff]\n")

    async def side_effect_two(request: httpx.Request) -> httpx.Response:
        events.append("start_two")
        await asyncio.sleep(0.05)
        events.append("end_two")
        return httpx.Response(200, text="[tool.ruff]\n")

    respx_mock.get("http://one.toml").mock(side_effect=side_effect_one)
    respx_mock.get("http://two.toml").mock(side_effect=side_effect_two)

    async with httpx.AsyncClient() as client:
        loop = asyncio.get_running_loop()
        start_time = loop.time()
        await fetch_upstreams_concurrently([URL("http://one.toml"), URL("http://two.toml")], client)
        elapsed = loop.time() - start_time
        # Two 0.05s sleeps (one per upstream) should overlap if run concurrently,
        # so total runtime should be clearly less than their sum.
        assert elapsed < 0.08

    # We don't assume a specific global ordering, only concurrency properties.

    # 1) All four events (two starts, two ends) should be present.
    assert len(events) == 4

    # Group events by their "stream id" (suffix after the first underscore).
    # This assumes events look like "start_<id>" / "end_<id>".
    per_stream: dict[str, dict[str, int]] = {}
    for idx, event in enumerate(events):
        kind, _, stream_id = event.partition("_")
        assert kind in {"start", "end"}
        assert stream_id, f"event {event!r} does not contain a stream id"
        per_stream.setdefault(stream_id, {})[kind] = idx

    # We expect exactly two streams, each with a start and an end.
    assert len(per_stream) == 2
    for stream_id, positions in per_stream.items():
        assert "start" in positions and "end" in positions, (
            f"stream {stream_id!r} did not record both start and end events"
        )
        # 2) Each start must happen before its corresponding end.
        assert positions["start"] < positions["end"]


@pytest.mark.asyncio
async def test_merge_multiple_upstreams_handles_errors(respx_mock: respx.Router):
    target_doc = document()

    args = ruff_sync.Arguments(
        command="pull",
        upstream=(URL("http://ok.toml"), URL("http://fail.toml")),
        to=pathlib.Path(),
        exclude=[],
        verbose=0,
        branch="main",
        path="",
    )

    # Mock HTTP responses using respx
    respx_mock.get("http://ok.toml").return_value = httpx.Response(
        200, text="[tool.ruff]\nline-length = 80"
    )
    respx_mock.get("http://fail.toml").return_value = httpx.Response(404)

    async with httpx.AsyncClient() as client:
        with pytest.raises(UpstreamError) as excinfo:
            await _merge_multiple_upstreams(target_doc, False, args, client)

        assert len(excinfo.value.errors) == 1
        url, err = excinfo.value.errors[0]
        assert str(url) == "http://fail.toml"
        assert isinstance(err, httpx.HTTPStatusError)


def test_cli_surfaces_upstream_error_with_exit_code_and_logs(
    monkeypatch: pytest.MonkeyPatch,
    respx_mock: respx.Router,
    capsys: pytest.CaptureFixture[str],
    configure_logging: logging.Logger,
) -> None:
    """Ensure UpstreamError from a failed fetch surfaces as exit code 1 with logged failures."""
    # Successful upstream
    respx_mock.get("http://ok.toml").respond(
        status_code=200,
        text="[tool.ruff]\nline-length = 88\n",
    )
    # Failing upstream
    respx_mock.get("http://fail.toml").respond(status_code=404)

    # Patch sys.argv to simulate CLI call
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ruff-sync",
            "pull",
            "http://ok.toml",
            "http://fail.toml",
            "--to",
            ".",
        ],
    )

    # Mock get_config to avoid reading from the real filesystem
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {})

    # Invoke the CLI entry point
    exit_code = ruff_sync.main()

    assert exit_code == 1

    captured = capsys.readouterr()
    combined_output = captured.out + captured.err

    # Assert that the failing upstream is mentioned in the logs
    assert "http://fail.toml" in combined_output
    assert "Failed to fetch" in combined_output


def test_cli_output_format_github(
    monkeypatch: pytest.MonkeyPatch,
    respx_mock: respx.Router,
    capsys: pytest.CaptureFixture[str],
    configure_logging: logging.Logger,
) -> None:
    """End-to-end: --output-format=github produces GitHub-style annotations."""
    respx_mock.get("https://example.com/pyproject.toml").respond(
        status_code=200,
        text="[tool.ruff]\ntarget-version = 'py311'\n",
    )

    # Patch sys.argv to simulate CLI call
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ruff-sync",
            "check",
            "https://example.com/pyproject.toml",
            "--output-format",
            "github",
        ],
    )

    # Mock get_config to avoid reading from the real filesystem
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {})

    # Invoke the CLI entry point - it should exit with 1 because pyproject.toml is missing
    # or out of sync. In a fake filesystem without pyproject.toml it will fail.
    exit_code = ruff_sync.main()
    assert exit_code == 1

    captured = capsys.readouterr()
    output = captured.out + captured.err

    # Assert: GitHub Actions annotation is present
    assert "::error" in output
    # The GitHub formatter should not emit JSON records.
    assert not output.lstrip().startswith("{")


def test_cli_output_format_json(
    monkeypatch: pytest.MonkeyPatch,
    respx_mock: respx.Router,
    capsys: pytest.CaptureFixture[str],
    configure_logging: logging.Logger,
) -> None:
    """End-to-end: --output-format=json produces JSON records."""
    respx_mock.get("https://example.com/pyproject.toml").respond(
        status_code=200,
        text="[tool.ruff]\ntarget-version = 'py311'\n",
    )

    # Patch sys.argv
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ruff-sync",
            "check",
            "https://example.com/pyproject.toml",
            "--output-format",
            "json",
        ],
    )

    # Mock get_config
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {})

    # Invoke
    exit_code = ruff_sync.main()
    assert exit_code == 1

    captured = capsys.readouterr()
    output = captured.out + captured.err
    lines = [line.strip() for line in output.splitlines() if line.strip()]

    # Assert: no GitHub-style annotations in JSON mode
    assert all("::error" not in line for line in lines)

    # Collect and parse all JSON records
    records = [json.loads(line) for line in lines if line.startswith("{")]

    assert records, "Expected at least one JSON record in CLI output"

    # 1. Assert expected fields like 'file' are present
    assert any("file" in record for record in records), (
        "Expected at least one JSON record to contain a 'file' field"
    )

    # 2. Assert presence of an error-level record
    assert any(record.get("level") == "error" for record in records), (
        "Expected at least one JSON record with level='error'"
    )

    # 3. Assert message content mentions "out of sync"
    assert any("out of sync" in str(record.get("message", "")).lower() for record in records), (
        "Expected at least one JSON record whose message mentions 'out of sync'"
    )


def test_cli_output_format_json_success(
    monkeypatch: pytest.MonkeyPatch,
    respx_mock: respx.Router,
    capsys: pytest.CaptureFixture[str],
    configure_logging: logging.Logger,
    fs: FakeFilesystem,
) -> None:
    """End-to-end: --output-format=json produces success-level JSON when in sync."""
    # Ensure a local pyproject.toml exists that matches upstream
    local_content = "[tool.ruff]\ntarget-version = 'py311'\n"
    fs.create_file("pyproject.toml", contents=local_content)

    # Mock in-sync upstream
    respx_mock.get("https://example.com/pyproject.toml").respond(
        status_code=200,
        text=local_content,
    )

    # Patch sys.argv
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "ruff-sync",
            "check",
            "https://example.com/pyproject.toml",
            "--output-format",
            "json",
        ],
    )

    # Mock get_config
    monkeypatch.setattr(ruff_sync_cli, "get_config", lambda _: {})

    # Invoke
    exit_code = ruff_sync.main()
    assert exit_code == 0

    captured = capsys.readouterr()
    output = captured.out + captured.err
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    records = [json.loads(line) for line in lines if line.startswith("{")]

    # At least one success-level record is emitted.
    assert any(record.get("level") == "success" for record in records), (
        "Expected at least one success-level record in JSON output"
    )

    # No error-level records are emitted on the success path.
    assert all(record.get("level") != "error" for record in records)


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
