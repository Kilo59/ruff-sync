"""Tests for the TUI ConfigNode AST types."""

from __future__ import annotations

import pytest

from ruff_sync.tui.types_ import DictNode, ListNode, ScalarNode, wrap_data


def test_wrap_data_scalar() -> None:
    """Test wrapping a scalar value."""
    node = wrap_data("key1", "value1", "tool.ruff")
    assert isinstance(node, ScalarNode)
    assert node.key == "key1"
    assert node.path == "tool.ruff"
    assert node.value == "value1"
    assert node.children() == []
    assert node.doc_target() == ("tool.ruff", "config")


def test_wrap_data_dict() -> None:
    """Test wrapping a dictionary."""
    data = {"nested_key1": "value1", "nested_key2": 42}
    node = wrap_data("tool.ruff", data, "tool.ruff")
    assert isinstance(node, DictNode)
    assert node.key == "tool.ruff"
    assert node.path == "tool.ruff"

    children = node.children()
    assert len(children) == 2
    assert isinstance(children[0], ScalarNode)
    assert children[0].key == "nested_key1"
    assert children[0].path == "tool.ruff.nested_key1"
    assert children[0].value == "value1"

    assert isinstance(children[1], ScalarNode)
    assert children[1].key == "nested_key2"
    assert children[1].path == "tool.ruff.nested_key2"
    assert children[1].value == 42


def test_wrap_data_list() -> None:
    """Test wrapping a list."""
    data = ["item1", "item2"]
    node = wrap_data("select", data, "tool.ruff.lint.select")
    assert isinstance(node, ListNode)
    assert node.key == "select"
    assert node.path == "tool.ruff.lint.select"

    children = node.children()
    assert len(children) == 2
    assert isinstance(children[0], ScalarNode)
    assert children[0].key == "[0]"
    assert children[0].path == "tool.ruff.lint.select[0]"
    assert children[0].value == "item1"

    assert isinstance(children[1], ScalarNode)
    assert children[1].key == "[1]"
    assert children[1].path == "tool.ruff.lint.select[1]"


def test_doc_target() -> None:
    """Test doc_target resolution."""
    root_dict = wrap_data("tool", {"ruff": {"line-length": 88}}, "tool.ruff")
    assert root_dict.doc_target() == ("", "none")

    child = root_dict.children()[0]
    assert child.doc_target() == ("tool.ruff.ruff", "config")


def test_rule_node_behavior() -> None:
    """Test that rule codes in lists get correct labels and targets."""
    data = ["RUF012"]
    root = wrap_data("select", data, "tool.ruff.lint.select")
    children = root.children()

    assert len(children) == 1
    node = children[0]
    assert isinstance(node, ScalarNode)
    # Label should be the rule code, not "[0]"
    assert node.key == "RUF012"
    # Target should be the rule code for documentation
    assert node.doc_target() == ("RUF012", "rule")


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
