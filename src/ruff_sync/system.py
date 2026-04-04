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
    return await _run_ruff_command(cmd, f"ruff rule {rule_code}")


async def get_ruff_config_markdown(setting_path: str) -> str | None:
    """Execute `ruff config <SETTING>` and return the Markdown documentation.

    Args:
        setting_path: The Ruff configuration setting path (e.g., 'lint.select').

    Returns:
        The Markdown documentation for the setting, or None if the execution fails.
    """
    # Strip 'tool.ruff.' prefix if present as 'ruff config' expects relative paths
    clean_path = setting_path.removeprefix("tool.ruff.")
    cmd: Final[list[str]] = ["ruff", "config", clean_path]
    return await _run_ruff_command(cmd, f"ruff config {clean_path}")


async def _run_ruff_command(cmd: list[str], description: str) -> str | None:
    """Execute a ruff command and return the decoded output.

    Args:
        cmd: The command to execute.
        description: A human-readable description for logging.

    Returns:
        The decoded stdout, or None if the command fails.
    """
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
            LOGGER.warning(f"Command '{description}' failed with code {process.returncode}: {msg}")
            return None

        return stdout.decode().strip()

    except FileNotFoundError:
        LOGGER.exception("Ruff executable not found in PATH.")
        return None
    except Exception:
        LOGGER.exception(f"Unexpected error executing '{description}'")
        return None
