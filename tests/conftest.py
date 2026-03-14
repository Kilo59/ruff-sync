from __future__ import annotations

import pytest

import ruff_sync


@pytest.fixture
def clear_ruff_sync_caches():
    """Clear all lru_caches in ruff_sync."""
    ruff_sync.get_config.cache_clear()
    ruff_sync.Arguments.fields.cache_clear()
    ruff_sync._resolve_source.cache_clear()
