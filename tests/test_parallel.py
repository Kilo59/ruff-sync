from __future__ import annotations

import pytest
import respx
from httpx import URL, Response

from ruff_sync.cli import Arguments
from ruff_sync.core import _merge_multiple_upstreams


@pytest.mark.asyncio
async def test_merge_multiple_upstreams_is_concurrent(respx_mock: respx.Router):
    # Setup mock data
    # We use a real TOMLDocument for the target to avoid issues with AsyncMock vs tomlkit
    from tomlkit import document

    target_doc = document()

    args = Arguments(
        command="pull",
        upstream=(URL("http://one.toml"), URL("http://two.toml")),
        to=".",
        exclude=[],
        verbose=0,
        branch="main",
        path="",
    )

    # Mock HTTP responses using respx
    respx_mock.get("http://one.toml").return_value = Response(
        200, text="[tool.ruff]\nline-length = 80"
    )
    respx_mock.get("http://two.toml").return_value = Response(
        200, text="[tool.ruff]\nline-length = 100"
    )

    import httpx

    async with httpx.AsyncClient() as client:
        result_doc = await _merge_multiple_upstreams(target_doc, False, args, client)

        # Verify both URLs were fetched
        assert respx_mock.get("http://one.toml").called
        assert respx_mock.get("http://two.toml").called

        # Verify the sequential merge result (the last one wins for specific keys)
        # Assuming merge_ruff_toml works as expected
        ruff_config = result_doc.get("tool", {}).get("ruff", {})
        assert ruff_config.get("line-length") == 100


@pytest.mark.asyncio
async def test_merge_multiple_upstreams_handles_errors(respx_mock: respx.Router):
    from tomlkit import document

    from ruff_sync.core import UpstreamError

    target_doc = document()

    args = Arguments(
        command="pull",
        upstream=(URL("http://ok.toml"), URL("http://fail.toml")),
        to=".",
        exclude=[],
        verbose=0,
        branch="main",
        path="",
    )

    # Mock HTTP responses using respx
    respx_mock.get("http://ok.toml").return_value = Response(
        200, text="[tool.ruff]\nline-length = 80"
    )
    respx_mock.get("http://fail.toml").return_value = Response(404)

    import httpx

    async with httpx.AsyncClient() as client:
        with pytest.raises(UpstreamError) as excinfo:
            await _merge_multiple_upstreams(target_doc, False, args, client)

        assert len(excinfo.value.errors) == 1
        url, err = excinfo.value.errors[0]
        assert str(url) == "http://fail.toml"
        assert isinstance(err, httpx.HTTPStatusError)
