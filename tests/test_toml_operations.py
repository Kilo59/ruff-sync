from __future__ import annotations

import pytest
from tomlkit import TOMLDocument, key, table


def test_dot_noted_toml_items():
    """
    Test that tomlkit can create a TOML document with dot-noted items.
    """
    expected: str = """[tool.ruff]
target-version = "py38"
line-length = 120
lint.select = ["F", "ASYNC"]
"""

    doc = TOMLDocument()
    tool = table(True)
    ruff = table()
    ruff.update(
        {
            "target-version": "py38",
            "line-length": 120,
            key(["lint", "select"]): ["F", "ASYNC"],
        }
    )
    tool.append("ruff", ruff)
    doc.append("tool", tool)
    doc_str = doc.as_string()
    print(doc_str)
    assert doc.as_string() == expected


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
