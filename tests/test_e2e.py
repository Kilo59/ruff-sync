from __future__ import annotations

import pathlib
import subprocess
from typing import TYPE_CHECKING, Final, NamedTuple

import pytest
import respx
import tomlkit
from httpx import URL

if TYPE_CHECKING:
    from collections.abc import Generator

    from pyfakefs.fake_filesystem import FakeFilesystem
    from pytest import FixtureRequest

TEST_ROOT: Final = pathlib.Path(__file__).parent


def test_manpage():
    """Test that the manpage can be generated with ruff-sync --help with no errors."""
    completed = subprocess.run(  # noqa: PLW1510 # want to see the stdout/stderr
        ["ruff-sync", "--help"],
        capture_output=True,
        text=True,
    )
    print(completed.stdout)
    assert completed.returncode == 0, completed.stderr


LIFECYLE_TOML_DIR: Final = TEST_ROOT / "lifecycle_tomls"
assert LIFECYLE_TOML_DIR.exists(), f"{LIFECYLE_TOML_DIR} does not exist"
LIFECYCLE_GROUPS: Final[set[str]] = {
    "_".join(f.name.split("_")[:-1]) for f in LIFECYLE_TOML_DIR.glob("*.toml")
}

UNSUPPORTED: Final[set[str]] = {"no_ruff_cfg"}
# LIFECYCLE_GROUPS.symmetric_difference_update(UNWANTED_GROUPS)


class _PrepEnv(NamedTuple):
    source_path: pathlib.Path
    upstream_url: URL
    expected_toml: str
    respx_mock: respx.MockRouter
    group_name: str


@pytest.fixture(params=LIFECYCLE_GROUPS)
def prep_env(
    fs: FakeFilesystem, request: FixtureRequest
) -> Generator[_PrepEnv, None, None]:
    group_name: str = request.param
    fs.add_real_directory(LIFECYLE_TOML_DIR)

    source_path = pathlib.Path(
        fs.create_file(  # type: ignore[arg-type]
            "my_dir/pyproject.toml",
            contents=LIFECYLE_TOML_DIR.joinpath(f"{group_name}_initial.toml").read_text(),
        ).path
    )
    base_url = "https://example.com"
    upstream_url = URL(f"{base_url}/pyproject.toml")

    with respx.mock(base_url=base_url, assert_all_called=False) as respx_mock:
        respx_mock.get(upstream_url.path).respond(
            200,
            content_type="text/plain",
            content=LIFECYLE_TOML_DIR.joinpath(f"{group_name}_upstream.toml").read_text(),
        )
        yield _PrepEnv(
            source_path=source_path,
            upstream_url=upstream_url,
            expected_toml=LIFECYLE_TOML_DIR.joinpath(
                f"{group_name}_final.toml"
            ).read_text(),
            respx_mock=respx_mock,
            group_name=group_name,
        )


@pytest.mark.asyncio
async def test_ruff_sync(prep_env: _PrepEnv):
    import ruff_sync

    if prep_env.group_name in UNSUPPORTED:
        pytest.skip(f"{prep_env.group_name} is not supported")

    await ruff_sync.sync(
        ruff_sync.Arguments(
            upstream=prep_env.upstream_url,
            source=prep_env.source_path,
            exclude={},
        )
    )

    expected_toml = tomlkit.parse(prep_env.expected_toml)
    actual_toml = tomlkit.parse(prep_env.source_path.read_text())

    print(f"Updated toml\n\n{prep_env.source_path.read_text()}")

    assert expected_toml.unwrap() == actual_toml.unwrap()
    assert prep_env.expected_toml == prep_env.source_path.read_text()


@pytest.mark.asyncio
async def test_unsupported(prep_env: _PrepEnv):
    import ruff_sync

    if prep_env.group_name not in UNSUPPORTED:
        pytest.skip(f"{prep_env.group_name} is supported")

    with pytest.raises(ruff_sync.RuffSyncError):
        await ruff_sync.sync(
            ruff_sync.Arguments(
                upstream=prep_env.upstream_url,
                source=prep_env.source_path,
                exclude={},
            )
        )


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
