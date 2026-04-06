from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from ruff_sync.system import compute_effective_rules

if TYPE_CHECKING:
    from ruff_sync.types_ import RuffRule


def test_compute_effective_rules_basic():
    """Test basic select/ignore logic."""
    all_rules = [
        {"code": "F401", "name": "unused-import", "linter": "Pyflakes"},
        {"code": "E501", "name": "line-too-long", "linter": "pycodestyle"},
        {"code": "UP001", "name": "useless-metaclass", "linter": "pyupgrade"},
    ]
    toml_config = {
        "tool": {
            "ruff": {
                "lint": {
                    "select": ["F"],
                    "ignore": ["F401"],
                }
            }
        }
    }

    enriched = compute_effective_rules(cast("list[RuffRule]", all_rules), toml_config)

    # F401: select matches "F" (len 1), ignore matches "F401" (len 4). Ignore wins.
    f401 = next(r for r in enriched if r["code"] == "F401")
    assert f401["status"] == "Ignored"
    assert f401["matching_select"] == "F"
    assert f401["matching_ignore"] == "F401"

    # E501: no match in select/ignore. Disabled (since select is explicitly "F").
    e501 = next(r for r in enriched if r["code"] == "E501")
    assert e501["status"] == "Disabled"
    assert e501["matching_select"] is None
    assert e501["matching_ignore"] is None


def test_compute_effective_rules_defaults():
    """Test that it falls back to Ruff defaults (E, F) when select is empty."""
    all_rules = [
        {"code": "F401", "name": "unused-import", "linter": "Pyflakes"},
        {"code": "E501", "name": "line-too-long", "linter": "pycodestyle"},
        {"code": "UP001", "name": "useless-metaclass", "linter": "pyupgrade"},
    ]
    toml_config: dict[str, Any] = {}  # Empty config

    enriched = compute_effective_rules(cast("list[RuffRule]", all_rules), toml_config)

    # Defaults are E and F
    f401 = next(r for r in enriched if r["code"] == "F401")
    assert f401["status"] == "Enabled"
    assert f401["matching_select"] == "F"

    e501 = next(r for r in enriched if r["code"] == "E501")
    assert e501["status"] == "Enabled"
    assert e501["matching_select"] == "E"

    up001 = next(r for r in enriched if r["code"] == "UP001")
    assert up001["status"] == "Disabled"
    assert up001["matching_select"] is None


def test_compute_effective_rules_specificity():
    """Test that the longest prefix match wins."""
    all_rules = [{"code": "PLR0912", "name": "too-many-branches", "linter": "Pylint"}]

    # Select more specific than ignore
    toml_config_1 = {"tool": {"ruff": {"lint": {"select": ["PLR0912"], "ignore": ["PLR"]}}}}
    enriched_1 = compute_effective_rules(cast("list[RuffRule]", all_rules), toml_config_1)
    assert enriched_1[0]["status"] == "Enabled"
    assert enriched_1[0]["matching_select"] == "PLR0912"
    assert enriched_1[0]["matching_ignore"] == "PLR"

    # Ignore more specific than select
    toml_config_2 = {"tool": {"ruff": {"lint": {"select": ["PLR"], "ignore": ["PLR0912"]}}}}
    enriched_2 = compute_effective_rules(cast("list[RuffRule]", all_rules), toml_config_2)
    assert enriched_2[0]["status"] == "Ignored"
    assert enriched_2[0]["matching_select"] == "PLR"
    assert enriched_2[0]["matching_ignore"] == "PLR0912"


def test_compute_effective_rules_extend():
    """Test that extend-select and extend-ignore are respected."""
    all_rules = [
        {"code": "F401", "name": "unused-import", "linter": "Pyflakes"},
        {"code": "I001", "name": "unsorted-imports", "linter": "isort"},
    ]
    toml_config = {
        "tool": {
            "ruff": {
                "lint": {
                    "extend-select": ["I"],
                    "extend-ignore": ["F401"],
                }
            }
        }
    }

    enriched = compute_effective_rules(cast("list[RuffRule]", all_rules), toml_config)

    # F401: Default "F" select matched, but extend-ignore "F401" is longer.
    f401 = next(r for r in enriched if r["code"] == "F401")
    assert f401["status"] == "Ignored"

    # I001: Selected via extend-select
    i001 = next(r for r in enriched if r["code"] == "I001")
    assert i001["status"] == "Enabled"
