from __future__ import annotations

import logging
import sys

import pytest
from typing_extensions import override

import ruff_sync


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
    logger.setLevel(logging.DEBUG)

    # Clear existing handlers to avoid duplicates/stale handlers
    logger.handlers = []

    # Add our dynamic handler
    handler = TestStreamHandler("stderr")
    logger.addHandler(handler)

    yield logger


@pytest.fixture
def clear_ruff_sync_caches():
    """Clear all lru_caches in ruff_sync."""
    ruff_sync.get_config.cache_clear()
    ruff_sync.Arguments.fields.cache_clear()
