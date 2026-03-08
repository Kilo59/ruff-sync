from __future__ import annotations

import pathlib
import subprocess
import sys
from typing import TYPE_CHECKING, Final, NamedTuple

import pytest
import respx
import tomlkit
from httpx import URL

import ruff_sync

if TYPE_CHECKING:
    from collections.abc import Generator

    from pyfakefs.fake_filesystem import FakeFilesystem
    from pytest import FixtureRequest

TEST_ROOT: Final = pathlib.Path(__file__).parent


def test_manpage():
    """Test that the manpage can be generated with ruff-sync --help with no errors."""
    completed = subprocess.run(
        [sys.executable, "ruff_sync.py", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    print(completed.stdout)
    assert completed.returncode == 0, completed.stderr


LIFECYCLE_TOML_DIR: Final = TEST_ROOT / "lifecycle_tomls"
assert LIFECYCLE_TOML_DIR.exists(), f"{LIFECYCLE_TOML_DIR} does not exist"
LIFECYCLE_GROUPS: Final[set[str]] = {
    "_".join(f.name.split("_")[:-1]) for f in LIFECYCLE_TOML_DIR.glob("*.toml")
}
# LIFECYCLE_GROUPS.remove("no_changes")
# LIFECYCLE_GROUPS.remove("standard")
# LIFECYCLE_GROUPS.remove("no_ruff_cfg")


class _PrepEnv(NamedTuple):
    source_path: pathlib.Path
    upstream_url: URL
    expected_toml: str
    respx_mock: respx.MockRouter


@pytest.fixture(params=LIFECYCLE_GROUPS)
def prep_env(
    fs: FakeFilesystem, request: FixtureRequest
) -> Generator[_PrepEnv, None, None]:
    group_name: str = request.param
    fs.add_real_directory(LIFECYCLE_TOML_DIR)

    source_path = pathlib.Path(
        fs.create_file(  # type: ignore[arg-type]
            "my_dir/pyproject.toml",
            contents=LIFECYCLE_TOML_DIR.joinpath(
                f"{group_name}_initial.toml"
            ).read_text(),
        ).path
    )
    base_url = "https://example.com"
    upstream_url = URL(f"{base_url}/pyproject.toml")

    with respx.mock(base_url=base_url) as respx_mock:
        respx_mock.get(upstream_url.path).respond(
            200,
            content_type="text/plain",
            content=LIFECYCLE_TOML_DIR.joinpath(
                f"{group_name}_upstream.toml"
            ).read_text(),
        )
        yield _PrepEnv(
            source_path=source_path,
            upstream_url=upstream_url,
            expected_toml=LIFECYCLE_TOML_DIR.joinpath(
                f"{group_name}_final.toml"
            ).read_text(),
            respx_mock=respx_mock,
        )


@pytest.mark.asyncio
async def test_ruff_sync(prep_env):
    await ruff_sync.sync(
        ruff_sync.Arguments(
            command="sync",
            upstream=prep_env.upstream_url,
            source=prep_env.source_path,
            exclude=set(),
            verbose=0,
        )
    )

    print(f"Updated toml\n\n{prep_env.source_path.read_text()}")

    assert tomlkit.parse(prep_env.expected_toml) == tomlkit.parse(
        prep_env.source_path.read_text()
    )
    assert prep_env.expected_toml == prep_env.source_path.read_text()


@pytest.mark.asyncio
async def test_ruff_check(prep_env):
    # 1. Initially it should be out of sync
    exit_code = await ruff_sync.check(
        ruff_sync.Arguments(
            command="check",
            upstream=prep_env.upstream_url,
            source=prep_env.source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )
    )
    # Most fixtures are out of sync initially
    # (except maybe one if it's a 'no changes' case, but we test the transitively)
    #
    # 2. Sync it
    await ruff_sync.sync(
        ruff_sync.Arguments(
            command="sync",
            upstream=prep_env.upstream_url,
            source=prep_env.source_path,
            exclude=set(),
            verbose=0,
        )
    )
    #
    # 3. Now it MUST be in sync (strictly)
    exit_code = await ruff_sync.check(
        ruff_sync.Arguments(
            command="check",
            upstream=prep_env.upstream_url,
            source=prep_env.source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )
    )
    assert exit_code == 0
    #
    # 4. Now it MUST be in sync (semantically)
    exit_code = await ruff_sync.check(
        ruff_sync.Arguments(
            command="check",
            upstream=prep_env.upstream_url,
            source=prep_env.source_path,
            exclude=set(),
            verbose=0,
            semantic=True,
            diff=True,
        )
    )
    assert exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
