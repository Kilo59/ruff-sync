"""System and subprocess utilities for ruff-sync."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

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
    if not clean_path or clean_path == "tool.ruff":
        return None
    cmd: Final[list[str]] = ["ruff", "config", clean_path]
    return await _run_ruff_command(cmd, f"ruff config {clean_path}")


async def get_all_ruff_rules() -> list[dict[str, Any]]:
    """Execute `ruff rule --all --output-format json` and return the parsed rules.

    Returns:
        A list of dictionaries representing all supported Ruff rules.
    """
    cmd: Final[list[str]] = ["ruff", "rule", "--all", "--output-format", "json"]
    output = await _run_ruff_command(cmd, "ruff rule --all")
    if not output:
        return []
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        LOGGER.exception("Failed to parse Ruff rules JSON.")
        return []

    if isinstance(data, list):
        return data
    return []


async def get_ruff_linters() -> list[dict[str, Any]]:
    """Execute `ruff linter --output-format json` and return the parsed linters.

    Returns:
        A list of dictionaries representing Ruff linter categories.
    """
    cmd: Final[list[str]] = ["ruff", "linter", "--output-format", "json"]
    output = await _run_ruff_command(cmd, "ruff linter")
    if not output:
        return []
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        LOGGER.exception("Failed to parse Ruff linters JSON.")
        return []

    if isinstance(data, list):
        return data
    return []


def compute_effective_rules(
    all_rules: list[dict[str, Any]], toml_config: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Determine the status (Enabled, Ignored, Disabled) for each rule.

    Args:
        all_rules: The list of all supported rules.
        toml_config: The local configuration dictionary.

    Returns:
        The list of rules enriched with a 'status' key.
    """
    # The config may be "wrapped" (top-level 'tool' key) or
    # "unwrapped" (direct Ruff config as returned by load_local_ruff_config).
    lint = toml_config.get("lint")
    if lint is None:
        lint = toml_config.get("tool", {}).get("ruff", {}).get("lint", {})

    select = set(lint.get("select", [])) | set(lint.get("extend-select", []))
    ignore = set(lint.get("ignore", [])) | set(lint.get("extend-ignore", []))

    # If no select/extend-select is provided, Ruff defaults to E and F
    if not lint.get("select") and not lint.get("extend-select"):
        select.update(["E", "F"])

    enriched: list[dict[str, Any]] = []
    for rule in all_rules:
        code = rule["code"]

        # Find longest matching select prefix
        best_select_len = -1
        for s in select:
            if code.startswith(s):
                best_select_len = max(best_select_len, len(s))

        # Find longest matching ignore prefix
        best_ignore_len = -1
        for i in ignore:
            if code.startswith(i):
                best_ignore_len = max(best_ignore_len, len(i))

        status = "Disabled"
        if best_select_len > best_ignore_len:
            status = "Enabled"
        elif best_ignore_len >= best_select_len and best_ignore_len != -1:
            status = "Ignored"

        rule_with_status = dict(rule)
        rule_with_status["status"] = status
        enriched.append(rule_with_status)

    return enriched


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

        output = stdout.decode().strip()
    except FileNotFoundError:
        LOGGER.exception("Ruff executable not found in PATH.")
        return None
    except Exception:
        LOGGER.exception(f"Unexpected error executing '{description}'")
        return None
    else:
        return output or None
