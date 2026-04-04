"""Tests for the system module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from ruff_sync.system import get_ruff_rule_markdown


@pytest.mark.asyncio
async def test_get_ruff_rule_markdown_success() -> None:
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"RUF012 rule docs", b"")
    mock_process.returncode = 0

    with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
        result = await get_ruff_rule_markdown("RUF012")
        assert result == "RUF012 rule docs"
        mock_exec.assert_called_once_with(
            "ruff",
            "rule",
            "RUF012",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )


@pytest.mark.asyncio
async def test_get_ruff_rule_markdown_error_code() -> None:
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"", b"Rule not found")
    mock_process.returncode = 1

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        result = await get_ruff_rule_markdown("NONEXISTENT")
        assert result is None


@pytest.mark.asyncio
async def test_get_ruff_rule_markdown_not_found() -> None:
    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
        result = await get_ruff_rule_markdown("RUF012")
        assert result is None
