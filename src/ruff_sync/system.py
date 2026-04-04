"""System and subprocess utilities for ruff-sync."""

from __future__ import annotations

import asyncio
import logging
from typing import Final

LOGGER = logging.getLogger(__name__)


async def get_ruff_rule_markdown(rule_code: str) -> str | None:
    """Execute `ruff rule <CODE>` and return the Markdown documentation.

    Args:
        rule_code: The Ruff rule code (e.g., 'RUF012').

    Returns:
        The Markdown documentation for the rule, or None if the execution fails
        or the rule is not found.
    """
    cmd: Final[list[str]] = ["ruff", "rule", rule_code]
    LOGGER.debug(f"Executing system command: {' '.join(cmd)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            msg = stderr.decode().strip()
            LOGGER.warning(f"Ruff command failed with exit code {process.returncode}: {msg}")
            return None

        return stdout.decode().strip()

    except FileNotFoundError:
        LOGGER.exception("Ruff executable not found in PATH.")
        return None
    except Exception:
        LOGGER.exception(f"Unexpected error executing ruff rule {rule_code}")
        return None
