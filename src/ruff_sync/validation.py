"""Validation logic for ruff-sync merged configurations."""

from __future__ import annotations

import logging
import pathlib
import re
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

_RUFF_TARGET_VERSION_PATTERN = re.compile(r"^py(\d)(\d+)$")


def _ruff_target_to_tuple(target_version: str) -> tuple[int, int] | None:
    """Parse a Ruff target-version string (e.g. 'py311') into a (major, minor) tuple."""
    m = _RUFF_TARGET_VERSION_PATTERN.match(target_version)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _requires_python_min_version(requires_python: str) -> tuple[int, int] | None:
    """Extract the minimum Python version from a PEP 440 requires-python string.

    Examples:
        '>=3.10' -> (3, 10)
        '^3.11'  -> (3, 11)
        '~=3.9'  -> (3, 9)
    """
    # TODO: Consider using packaging.specifiers.SpecifierSet optionally if available
    # Match all version specifiers of the form X.Y
    matches = re.findall(r"(\d+)\.(\d+)", requires_python)
    if matches:
        # Convert to list of (int, int) and return the minimum semantic version
        versions = [(int(major), int(minor)) for major, minor in matches]
        return min(versions)
    return None


def check_python_version_consistency(doc: TOMLDocument, strict: bool = False) -> bool:
    """Warn if the merged ruff target-version conflicts with requires-python.

    Args:
        doc: The merged TOML document (pyproject.toml format).
        strict: If True, treat version mismatch as a failure.

    Returns:
        True if versions are consistent or if check is skipped.
        False if strict=True and versions are inconsistent.
    """
    try:
        ruff_section = doc.get("tool", {}).get("ruff", {})
        target_version = ruff_section.get("target-version")
        requires_python = doc.get("project", {}).get("requires-python")
    except (AttributeError, TypeError):
        return True  # Don't crash on unexpected doc shapes

    if not target_version or not requires_python:
        missing = []
        if not target_version:
            missing.append("[tool.ruff] target-version")
        if not requires_python:
            missing.append("[project] requires-python")
        LOGGER.warning(f"Skipping Python version consistency check: missing {', '.join(missing)}.")
        return True  # Nothing to compare

    ruff_min = _ruff_target_to_tuple(str(target_version))
    proj_min = _requires_python_min_version(str(requires_python))

    if ruff_min is None or proj_min is None:
        return True  # Couldn't parse one of the versions

    if ruff_min < proj_min:
        msg = (
            f"Version mismatch: upstream [tool.ruff] target-version='{target_version}' "
            f"targets Python {ruff_min[0]}.{ruff_min[1]}, but local [project] requires-python="
            f"'{requires_python}' requires Python >= {proj_min[0]}.{proj_min[1]}. "
            "Consider updating target-version in the upstream config."
        )
        if strict:
            LOGGER.error(f"❌ {msg}")
            return False
        LOGGER.warning(f"⚠️  {msg}")

    return True


def validate_toml_syntax(doc: TOMLDocument) -> bool:
    """Return True if the document serializes to valid TOML.

    tomlkit always produces valid TOML, so this catches any edge cases
    where serialization itself raises an unexpected exception.
    """
    try:
        tomlkit.parse(doc.as_string())
        return True  # noqa: TRY300
    except tomlkit.exceptions.TOMLKitError:
        LOGGER.exception("❌ Merged config failed TOML syntax check")
        return False


def validate_ruff_accepts_config(
    doc: TOMLDocument, is_ruff_toml: bool = False, strict: bool = False
) -> bool:
    """Return True if Ruff accepts the merged configuration.

    Writes the merged config to a temporary file and runs:
        ruff check --isolated --config <tmp> <dummy-py-file>

    Args:
        doc: The merged TOML document to validate.
        is_ruff_toml: True if the document is a ruff.toml (not pyproject.toml).
        strict: If True, treat configuration warnings (deprecated rules, etc.) as failures.

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
        # Using --config should be enough to isolate from project config
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

        # Exit 0 = no issues found, exit 1 = issues found — both mean ruff
        # parsed the config successfully. Exit 2 = config/usage error.
        if result.returncode not in (0, 1):
            LOGGER.error(
                f"❌ Ruff rejected the merged config (exit {result.returncode}):\n"
                f"{result.stderr.strip()}"
            )
            return False

        # If strict mode is enabled, check stderr for configuration warnings
        if strict and result.stderr:
            # Ruff emits "warning: ..." or "deprecated ..." to stderr for config issues
            # that aren't fatal enough to cause exit code 2.
            lower_stderr = result.stderr.lower()
            if "warning:" in lower_stderr or "deprecated" in lower_stderr:
                LOGGER.error(
                    "❌ Ruff validation warning(s) detected in strict mode:\n"
                    f"{result.stderr.strip()}"
                )
                return False

        return True


def validate_merged_config(
    doc: TOMLDocument, is_ruff_toml: bool = False, strict: bool = False
) -> bool:
    """Run all validation checks on the merged TOML document.

    Returns True only if all checks pass. Returns False and logs errors
    if any check fails.

    Args:
        doc: The merged TOML document to validate.
        is_ruff_toml: True if the document is a standalone ruff.toml.
        strict: If True, treat configuration warnings as hard failures.

    Returns:
        True if all validation checks pass, False otherwise.
    """
    if not validate_toml_syntax(doc):
        return False
    if not validate_ruff_accepts_config(doc, is_ruff_toml=is_ruff_toml, strict=strict):
        return False
    if not is_ruff_toml:
        return check_python_version_consistency(doc, strict=strict)
    return True
