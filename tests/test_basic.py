from __future__ import annotations

import contextlib
import os
import pathlib
import shutil
from pprint import pformat as pf
from typing import TYPE_CHECKING, Final

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


def test_ruff_sync():
    assert ruff_sync.__version__ == "0.0.1.dev0"


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
    orginal_keys = set(original_toml_doc["tool"]["ruff"]["lint"].keys())  # type: ignore[index,union-attr]
    print(f"{pf(orginal_keys)}")

    parsed_toml_doc = ruff_sync.toml_ruff_parse(toml_s, exclude=exclude)
    print(f"\n{pf(parsed_toml_doc, compact=True)}")

    lint_config: TOMLDocument = parsed_toml_doc["lint"]  # type: ignore[assignment]

    for section in exclude:
        assert section not in lint_config

    expected_sections = orginal_keys - set(exclude)
    for section in expected_sections:
        assert (
            section in original_toml_doc["tool"]["ruff"]["lint"]  # type: ignore[index,operator]
        ), f"{section} was not in original doc, fix test"

        assert section in lint_config, f"{section} was incorrectly excluded"


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


@pytest.mark.parametrize("sample_toml_str", TOML_STRS_PARAMS)
def test_filter_extra_items(sample_toml_str: str, sep_str: str):
    exclude: list[str] = []  # TODO: pick random sections to exclude
    original_toml = tomlkit.parse(sample_toml_str)
    original_ruff = original_toml["tool"].get("ruff")
    print(f"Original toml:\n{sep_str}\n{original_toml.as_string()}")

    filtered_toml = ruff_sync.filter_extra_items(original_toml, lint_exclude=exclude)
    print(f"Filtered toml:\n{sep_str}\n{filtered_toml.as_string()}")

    top_level_keys = set(filtered_toml.keys())
    print(f"Top level keys: {top_level_keys}")
    if original_ruff:
        assert top_level_keys == {"tool"}, "Top level keys other than 'tool' found"

        for section in exclude:
            assert section not in filtered_toml["tool"]["ruff"]["lint"]

        for section in original_ruff["lint"]:
            if section not in exclude:
                assert section in filtered_toml["tool"]["ruff"]["lint"]
    else:
        # If there was no ruff section in the original toml,
        # the filtered toml should be empty
        assert not filtered_toml, "Filtered toml was not empty"


@pytest.mark.parametrize(
    "source",
    [
        param(
            SAMPLE_TOML_WITHOUT_RUFF_CFG.joinpath("pyproject.toml").read_text(),
            id="no ruff cfg",
            marks=pytest.mark.xfail(reason="maybe not needed"),
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
    upstream_toml = httpx.get(upstream).text  # noqa: ASYNC100 # blocking but doesn't matter
    await ruff_sync.sync(
        ruff_sync.Arguments(upstream=upstream, source=fake_fs_source, exclude=())
    )
    updated_toml = fake_fs_source.read_text()
    updated_ruff_config: Table = tomlkit.parse(updated_toml)["tool"]["ruff"]  # type: ignore[index,assignment]
    print(f"\nUpdated tool.ruff\n{sep_str}\n{tomlkit.dumps(updated_ruff_config)}")
    assert original_toml != updated_toml

    assert set(original_ruff_config.keys()).issubset(set(updated_ruff_config.keys()))

    # Ensure the updated ruff config has the same keys as the original
    for key in original_ruff_config:
        assert (
            key in updated_ruff_config
        ), f"Original key {key} was not in updated ruff config"

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


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
