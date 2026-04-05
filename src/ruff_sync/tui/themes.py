"""Custom themes for the ruff-sync TUI."""

from __future__ import annotations

from textual.theme import Theme

# RUFF_SYNC_SLATE (Recommended)
# Matches the MkDocs Material "Slate/Amber/Deep-Purple" documentation palette.
RUFF_SYNC_SLATE = Theme(
    name="ruff-sync-slate",
    primary="#FFC107",  # Amber 500
    secondary="#9575CD",  # Muted Purple
    accent="#B388FF",  # Lavender
    background="#0f172a",  # Slate 900
    surface="#1e293b",  # Slate 800
    panel="#334155",  # Slate 700
    boost="#334155",  # Slate 700
)

# AMBER_EMBER
# High-contrast, warm dark theme with vibrant gold primary colors.
AMBER_EMBER = Theme(
    name="amber-ember",
    primary="#FFB300",  # Darker, punchy Amber
    secondary="#FFD54F",  # Lighter Amber
    accent="#D81B60",  # Material Magenta
    background="#121212",  # Material Dark
    surface="#1E1E1E",
    panel="#2C2C2C",
    boost="#2C2C2C",
)

# MATERIAL_GHOST (Light)
# A clean light theme for high-visibility environments.
MATERIAL_GHOST = Theme(
    name="material-ghost",
    primary="#FFC107",  # Amber 500
    secondary="#673AB7",  # Deep Purple 500
    accent="#7E57C2",  # Material Purple
    background="#FAFAFA",
    surface="#FFFFFF",
    panel="#F5F5F5",
    boost="#EEEEEE",
)
