"""Validation logic for ruff-sync merged configurations."""

from __future__ import annotations

import logging
import pathlib
import subprocess
import tempfile

import tomlkit
from tomlkit import TOMLDocument

__all__ = [
    "validate_merged_config",
    "validate_ruff_accepts_config",
    "validate_toml_syntax",
]

LOGGER = logging.getLogger(__name__)


def validate_toml_syntax(doc: TOMLDocument) -> bool:
    """Return True if the document serializes to valid TOML.

    tomlkit always produces valid TOML, so this catches any edge cases
    where serialization itself raises an unexpected exception.
    """
    try:
        tomlkit.parse(doc.as_string())
        return True  # noqa: TRY300
    except Exception:
        LOGGER.error("❌ Merged config failed TOML syntax check.")  # noqa: TRY400
        return False


def validate_ruff_accepts_config(doc: TOMLDocument, is_ruff_toml: bool = False) -> bool:
    """Return True if Ruff accepts the merged configuration.

    Writes the merged config to a temporary file and runs:
        ruff check --config <tmp> <dummy-py-file>

    Args:
        doc: The merged TOML document to validate.
        is_ruff_toml: True if the document is a ruff.toml (not pyproject.toml).

    Returns:
        True if Ruff accepts the config without errors, False otherwise.
    """
    # The filename matters: ruff.toml uses flat format, pyproject.toml uses [tool.ruff]
    config_filename = "ruff.toml" if is_ruff_toml else "pyproject.toml"

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = pathlib.Path(tmp_dir) / config_filename
        tmp_path.write_text(doc.as_string(), encoding="utf-8")

        # Create a minimal dummy Python file for ruff to lint
        dummy_py = pathlib.Path(tmp_dir) / "dummy.py"
        dummy_py.write_text("# ruff-sync config validation\n", encoding="utf-8")

        config_flag = f"--config={tmp_path}"
        cmd = ["ruff", "check", config_flag, str(dummy_py)]
        LOGGER.debug(f"Running ruff config validation: {' '.join(cmd)}")

        try:
            result = subprocess.run(  # noqa: S603
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except FileNotFoundError:
            LOGGER.warning("⚠️  `ruff` not found on PATH — skipping Ruff config validation.")
            return True  # Soft fail: don't block if ruff isn't installed
        except subprocess.TimeoutExpired:
            LOGGER.warning("⚠️  Ruff config validation timed out — skipping.")
            return True  # Soft fail on timeout

        if result.returncode in (0, 1):
            # Exit 0 = no issues found, exit 1 = issues found — both mean ruff
            # parsed the config successfully. Exit 2 = config/usage error.
            return True

        LOGGER.error(
            f"❌ Ruff rejected the merged config (exit {result.returncode}):\n"
            f"{result.stderr.strip()}"
        )
        return False


def validate_merged_config(doc: TOMLDocument, is_ruff_toml: bool = False) -> bool:
    """Run all validation checks on the merged TOML document.

    Returns True only if all checks pass. Returns False and logs errors
    if any check fails.

    Args:
        doc: The merged TOML document to validate.
        is_ruff_toml: True if the document is a standalone ruff.toml.

    Returns:
        True if all validation checks pass, False otherwise.
    """
    if not validate_toml_syntax(doc):
        return False
    return validate_ruff_accepts_config(doc, is_ruff_toml=is_ruff_toml)
