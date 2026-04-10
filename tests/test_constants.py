from __future__ import annotations

from ruff_sync.constants import (
    DEFAULT_BRANCH,
    DEFAULT_EXCLUDE,
    MISSING,
    resolve_bool_flags,
    resolve_defaults,
)


def test_resolve_defaults_all_missing():
    """Verify that MISSING for all args resolves to project defaults."""
    branch, path, exclude = resolve_defaults(MISSING, MISSING, MISSING)

    assert branch == DEFAULT_BRANCH
    assert path is None  # DEFAULT_PATH ("") is normalized to None
    assert exclude == DEFAULT_EXCLUDE


def test_resolve_defaults_passthrough():
    """Verify that non-MISSING values are passed through unchanged."""
    branch, path, exclude = resolve_defaults("develop", "src", ["rule1"])

    assert branch == "develop"
    assert path == "src"
    assert list(exclude) == ["rule1"]


def test_resolve_defaults_mixed():
    """Verify mixed combinations of MISSING and explicit values."""
    # Case: branch is MISSING, others are explicit
    branch, path, exclude = resolve_defaults(MISSING, "subdir", ["exclude1"])
    assert branch == DEFAULT_BRANCH
    assert path == "subdir"
    assert exclude == ["exclude1"]

    # Case: path is MISSING, others are explicit
    branch, path, exclude = resolve_defaults("feat/branch", MISSING, ["exclude2"])
    assert branch == "feat/branch"
    assert path is None  # MISSING normalized to None
    assert exclude == ["exclude2"]

    # Case: exclude is MISSING, others are explicit
    branch, path, exclude = resolve_defaults("main", "root", MISSING)
    assert branch == "main"
    assert path == "root"
    assert exclude == DEFAULT_EXCLUDE


def test_resolve_defaults_path_normalization():
    """Verify that empty string paths are normalized to None."""
    # Explicit empty string
    _, path, _ = resolve_defaults("main", "", MISSING)
    assert path is None

    # MISSING (which is DEFAULT_PATH which is "")
    _, path, _ = resolve_defaults("main", MISSING, MISSING)
    assert path is None

    # Non-empty string remains
    _, path, _ = resolve_defaults("main", "backend", MISSING)
    assert path == "backend"


def test_resolve_bool_flags_all_missing():
    """Verify that MISSING for all flags resolves to project defaults."""
    validate, strict, pre_commit = resolve_bool_flags(MISSING, MISSING, MISSING)
    assert validate is False
    assert strict is False
    assert pre_commit is False


def test_resolve_bool_flags_strict_implies_validate():
    """Verify that strict=True implies validate=True."""
    validate, strict, _ = resolve_bool_flags(MISSING, True, MISSING)
    assert validate is True
    assert strict is True

    # If validate is explicitly False, it wins and disables strict mode
    validate, strict, _ = resolve_bool_flags(False, True, MISSING)
    assert validate is False
    assert strict is False


def test_resolve_bool_flags_explicit_false():
    """Verify that explicit False values are preserved."""
    validate, strict, pre_commit = resolve_bool_flags(False, False, False)
    assert validate is False
    assert strict is False
    assert pre_commit is False
