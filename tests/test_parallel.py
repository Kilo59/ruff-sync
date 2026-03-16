from __future__ import annotations

from io import StringIO
from unittest.mock import AsyncMock, patch

import pytest
from httpx import URL

from ruff_sync.cli import Arguments
from ruff_sync.core import FetchResult, _merge_multiple_upstreams


@pytest.mark.asyncio
async def test_merge_multiple_upstreams_is_concurrent():
    # Setup mock data
    target_doc = AsyncMock()
    args = Arguments(
        command="pull",
        upstream=(URL("http://one.toml"), URL("http://two.toml")),
        to=".",
        exclude=[],
        verbose=0,
        branch="main",
        path="",
    )
    client = AsyncMock()

    # Mock return values for fetch_upstream_config
    res1 = FetchResult(StringIO("[tool.ruff]\nline-length = 80"), URL("http://one.toml"))
    res2 = FetchResult(StringIO("[tool.ruff]\nline-length = 100"), URL("http://two.toml"))

    # We want to verify that fetch_upstream_config is called for all upstreams
    # before we start merging.

    with patch("ruff_sync.core.fetch_upstream_config") as mock_fetch:
        mock_fetch.side_effect = [res1, res2]

        with patch("ruff_sync.core.get_ruff_config") as mock_get_cfg:
            mock_get_cfg.return_value = {"line-length": 80}  # simplified

            with patch("ruff_sync.core.merge_ruff_toml") as mock_merge:
                mock_merge.return_value = target_doc

                await _merge_multiple_upstreams(target_doc, False, args, client)

                # Check that fetch was called twice
                assert mock_fetch.call_count == 2
                # Check that merge was called twice
                assert mock_merge.call_count == 2
