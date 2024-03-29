from __future__ import annotations

import contextlib
import os
import pathlib
from pprint import pformat as pf
from typing import TYPE_CHECKING, Final

import pytest
import respx
import tomlkit
from httpx import URL
from tomlkit import TOMLDocument

import ruff_sync

if TYPE_CHECKING:
    from collections.abc import Generator

    from pyfakefs.fake_filesystem import FakeFilesystem

TEST_ROOT: Final = pathlib.Path(__file__).parent
PROJECT_ROOT: Final = TEST_ROOT.parent
ROOT_PYPROJECT_TOML: Final = PROJECT_ROOT / "pyproject.toml"
assert ROOT_PYPROJECT_TOML.exists(), f"{ROOT_PYPROJECT_TOML} does not exist"

SAMPLE_TOML_W_RUFF_SYNC_CFG: Final = TEST_ROOT / "w_ruff_sync_cfg"
SAMPLE_TOML_WITHOUT_RUFF_SYNC_CFG: Final = TEST_ROOT / "wo_ruff_sync_cfg"
SAMPLE_TOML_WITHOUT_RUFF_CFG: Final = TEST_ROOT / "wo_ruff_cfg"


@pytest.fixture(scope="session")
def pyproject_toml_s() -> str:
    """
    The contents of the root pyproject.toml file.
    Prevents problems with the file or file system being modified during tests.
    """
    s = ROOT_PYPROJECT_TOML.read_text()
    assert s, f"{ROOT_PYPROJECT_TOML} was empty"
    return s


def test_ruff_sync():
    assert ruff_sync.__version__ == "0.0.1.dev0"


@pytest.fixture
def toml_s() -> str:
    """A sample pyproject.toml file with ruff config."""
    return """
    [tool.ruff.lint]
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


@pytest.mark.asyncio
async def test_sync(mock_http: respx.MockRouter, fake_fs_source: pathlib.Path):
    upstream = URL("https://example.com/pyproject.toml")
    await ruff_sync.sync(
        ruff_sync.Arguments(upstream=upstream, source=fake_fs_source, exclude=())
    )


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
        (
            SAMPLE_TOML_W_RUFF_SYNC_CFG,
            {
                "upstream": "https://raw.githubusercontent.com/pydantic/pydantic/main/pyproject.toml",
                "exclude": ["per-file-ignores", "ignore", "line-length"],
            },
        ),
        (
            SAMPLE_TOML_WITHOUT_RUFF_CFG,
            {
                "upstream": "https://raw.githubusercontent.com/pydantic/pydantic/main/pyproject.toml",
                "exclude": ["per-file-ignores", "ignore", "line-length"],
            },
        ),
        (SAMPLE_TOML_WITHOUT_RUFF_SYNC_CFG, {}),
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
