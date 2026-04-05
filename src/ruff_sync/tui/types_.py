"""Data types for the TUI."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ruff_sync.types_ import RuffLinter, RuffRule


@runtime_checkable
class ConfigNode(Protocol):
    """Protocol for TUI Configuration Nodes."""

    @property
    def key(self) -> str:
        """The key or label for this node."""
        ...

    @property
    def path(self) -> str:
        """The full configuration path."""
        ...

    def children(self) -> list[ConfigNode]:
        """Child nodes for tree expansion."""
        ...

    def doc_target(self) -> tuple[str, Literal["rule", "config", "none"]]:
        """Returns the documentation target and type."""
        ...


class DictNode:
    """A node representing a dictionary in the configuration."""

    def __init__(self, key: str, path: str, data: dict[str, Any]) -> None:
        """Initialize the Dictionary Node."""
        self._key = key
        self._path = path
        self.data = data

    @property
    def key(self) -> str:
        """Get the node's key."""
        return self._key

    @property
    def path(self) -> str:
        """Get the node's configuration path."""
        return self._path

    def children(self) -> list[ConfigNode]:
        """Return the dictionary children wrapped as ConfigNodes."""
        return [wrap_data(k, v, f"{self.path}.{k}") for k, v in sorted(self.data.items())]

    def doc_target(self) -> tuple[str, Literal["rule", "config", "none"]]:
        """Resolve the primary target string and type for documentation."""
        if self._path == "tool.ruff":
            return ("", "none")
        return (self._path, "config")


class ListNode:
    """A node representing a list in the configuration."""

    def __init__(self, key: str, path: str, data: list[Any]) -> None:
        """Initialize the List Node."""
        self._key = key
        self._path = path
        self.data = data

    @property
    def key(self) -> str:
        """Get the node's key."""
        return self._key

    @property
    def path(self) -> str:
        """Get the node's configuration path."""
        return self._path

    def children(self) -> list[ConfigNode]:
        """Return the list children wrapped as ConfigNodes."""
        return [wrap_data(f"[{i}]", v, f"{self.path}[{i}]") for i, v in enumerate(self.data)]

    def doc_target(self) -> tuple[str, Literal["rule", "config", "none"]]:
        """Resolve the primary target string and type for documentation."""
        return (self._path, "config")


class ScalarNode:
    """A node representing a scalar value in the configuration."""

    def __init__(self, key: str, path: str, value: Any) -> None:
        """Initialize the Scalar Node."""
        self._key = key
        self._path = path
        self.value = value

    @property
    def key(self) -> str:
        """Get the node's key."""
        return self._key

    @property
    def path(self) -> str:
        """Get the node's configuration path."""
        return self._path

    def children(self) -> list[ConfigNode]:
        """Return empty list, as scalars have no children."""
        return []

    def doc_target(self) -> tuple[str, Literal["rule", "config", "none"]]:
        """Resolve the primary target string and type for documentation."""
        return (self._path, "config")


class RulesCollectionNode:
    """A node representing the root 'Effective Rule Status' section."""

    def __init__(self, linters: list[RuffLinter], effective_rules: list[RuffRule]) -> None:
        """Initialize the Rules Collection Node."""
        self._key = "Effective Rule Status"
        self._path = "__rules__"
        self.linters = linters
        self.effective_rules = effective_rules

    @property
    def key(self) -> str:
        """Get the node's key."""
        return self._key

    @property
    def path(self) -> str:
        """Get the node's configuration path."""
        return self._path

    def children(self) -> list[ConfigNode]:
        """Return Linters as children."""
        return _build_linter_nodes(self.linters, self.effective_rules)

    def doc_target(self) -> tuple[str, Literal["rule", "config", "none"]]:
        """No documentation target for root collection."""
        return ("", "none")


class LinterNode:
    """A node representing a category or linter group."""

    def __init__(self, linter: RuffLinter, effective_rules: list[RuffRule]) -> None:
        """Initialize a Linter Node."""
        self.linter = linter
        name = linter["name"]
        prefix = linter.get("prefix")
        self._key = f"{name} ({prefix})" if prefix else name
        self._path = f"__linter__:{prefix}"
        self.effective_rules = effective_rules

    @property
    def key(self) -> str:
        """Get the node's key."""
        return self._key

    @property
    def path(self) -> str:
        """Get the node's configuration path."""
        return self._path

    def children(self) -> list[ConfigNode]:
        """Return subcategories of this Linter as children if they exist."""
        if "categories" in self.linter:
            return _build_linter_nodes(self.linter["categories"], self.effective_rules)
        return []

    def doc_target(self) -> tuple[str, Literal["rule", "config", "none"]]:
        """No documentation target for linter group itself."""
        return ("", "none")


class RuleNode:
    """A node representing an individual Ruff rule."""

    def __init__(self, rule: RuffRule) -> None:
        """Initialize a Rule Node."""
        self.rule = rule
        self._key = rule["code"]
        self._path = f"__rule__:{rule['code']}"

    @property
    def key(self) -> str:
        """Get the node's key."""
        return self._key

    @property
    def path(self) -> str:
        """Get the node's configuration path."""
        return self._path

    def children(self) -> list[ConfigNode]:
        """Return empty list; rules have no children."""
        return []

    def doc_target(self) -> tuple[str, Literal["rule", "config", "none"]]:
        """Target the rule exactly for documentation."""
        return (self.rule["code"], "rule")


def _is_linter_active(linter: RuffLinter, effective_rules: list[RuffRule]) -> bool:
    prefix = linter.get("prefix")
    if prefix and any(
        r["code"].startswith(prefix) and r["status"] != "Disabled" for r in effective_rules
    ):
        return True

    if "categories" in linter:
        return any(_is_linter_active(c, effective_rules) for c in linter["categories"])

    return False


def _build_linter_nodes(
    linters: list[RuffLinter], effective_rules: list[RuffRule]
) -> list[ConfigNode]:
    nodes: list[ConfigNode] = []
    for linter in sorted(linters, key=lambda x: x["name"]):
        if not _is_linter_active(linter, effective_rules):
            continue
        nodes.append(LinterNode(linter, effective_rules))
    return nodes


def wrap_data(key: str, data: Any, path: str = "tool.ruff") -> ConfigNode:
    """Wrap raw configuration data into strongly-typed ConfigNode instances."""
    if isinstance(data, dict):
        return DictNode(key, path, data)
    if isinstance(data, list):
        return ListNode(key, path, data)
    return ScalarNode(key, path, data)
