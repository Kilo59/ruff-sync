from __future__ import annotations

import logging
import os
import sys
from typing import Literal, Protocol, runtime_checkable

import pytest
from typing_extensions import override

import ruff_sync

LOGGER = logging.getLogger(__name__)


class TestStreamHandler(logging.Handler):
    """A logging handler that always writes to the current system stderr/stdout.

    This is necessary because pytest's capsys replaces sys.stdout/stderr for each test,
    but standard StreamHandlers cache the stream at initialization time.
    """

    def __init__(self, stream_name: str = "stderr"):
        """Initialize the handler with the target stream name."""
        super().__init__()
        self.stream_name = stream_name

    @override
    def emit(self, record):
        """Emit a log record to the specified system stream."""
        try:
            msg = self.format(record)
            stream = getattr(sys, self.stream_name)
            stream.write(msg + "\n")
            self.flush()
        except Exception:
            self.handleError(record)


@pytest.fixture
def configure_logging():
    """Configure ruff_sync logger for tests to ensure capsys can capture log output."""
    logger = logging.getLogger("ruff_sync")
    old_handlers = logger.handlers[:]
    old_level = logger.level

    try:
        logger.setLevel(logging.DEBUG)

        # Clear existing handlers to avoid duplicates/stale handlers
        logger.handlers = []

        # Add our dynamic handler
        handler = TestStreamHandler("stderr")
        logger.addHandler(handler)

        yield logger
    finally:
        # Restore original state
        logger.handlers = old_handlers
        logger.setLevel(old_level)


@pytest.fixture
def clear_ruff_sync_caches():
    """Clear all lru_caches in ruff_sync."""
    ruff_sync.get_config.cache_clear()
    ruff_sync.Arguments.fields.cache_clear()


@pytest.fixture
def isolate_ci_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure CI environment variables (like GITHUB_STEP_SUMMARY) are not set.

    This prevents tests from polluting real CI reports when they invoke formatters.
    """
    if "GITHUB_STEP_SUMMARY" in os.environ:
        LOGGER.warning("Clearing GITHUB_STEP_SUMMARY to prevent test pollution")
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)


@runtime_checkable
class CLIRunner(Protocol):
    """Protocol for the cli_run fixture."""

    def __call__(
        self,
        args: list[str],
        entry_point: Literal["ruff-sync", "ruff-inspect"] = "ruff-sync",
    ) -> tuple[int, str, str]:
        """Run a CLI command with the given arguments."""
        ...


@pytest.fixture
def cli_run(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], isolate_ci_env: None
) -> CLIRunner:
    """Fixture to run the ruff-sync CLI or entry points and capture output."""

    def _run(
        args: list[str],
        entry_point: Literal["ruff-sync", "ruff-inspect"] = "ruff-sync",
    ) -> tuple[int, str, str]:
        """Run a CLI command with the given arguments.

        Args:
            args: The list of CLI arguments (excluding the program name).
            entry_point: The name of the entry point to run ('ruff-sync' or 'ruff-inspect').

        Returns:
            A tuple of (exit_code, stdout, stderr).
        """
        # Reset sys.argv for each run
        monkeypatch.setattr(sys, "argv", [entry_point, *args])

        exit_code = 0
        try:
            if entry_point == "ruff-inspect":
                from ruff_sync.cli import inspect

                exit_code = inspect()
            else:
                from ruff_sync.cli import main

                exit_code = main()
        except SystemExit as e:
            # Handle sys.exit calls from argparse or main
            if isinstance(e.code, int):
                exit_code = e.code
            elif e.code is None:
                exit_code = 0
            else:
                exit_code = 1

        captured = capsys.readouterr()
        return exit_code, captured.out, captured.err

    return _run
