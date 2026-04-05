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
    warning="#FFC107",  # Amber 500
    error="#F44336",  # Red 500
    success="#4CAF50",  # Green 500
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
    warning="#FFB300",  # Amber 600
    error="#E91E63",  # Pink 500
    success="#81C784",  # Light Green 300
    background="#121212",  # Material Dark
    surface="#1E1E1E",
    panel="#2C2C2C",
    boost="#2C2C2C",
)

# MATERIAL_GHOST (Light)
# A clean light theme for high-visibility environments.
# Optimized status colors for high contrast on white backgrounds.
MATERIAL_GHOST = Theme(
    name="material-ghost",
    primary="#F57F17",  # Yellow 900 (High contrast)
    secondary="#673AB7",  # Deep Purple 500
    accent="#7E57C2",  # Material Purple
    warning="#F57F17",  # Yellow 900 (High contrast)
    error="#C62828",  # Red 800
    success="#2E7D32",  # Green 800 (High contrast)
    background="#FAFAFA",
    surface="#FFFFFF",
    panel="#F5F5F5",
    boost="#EEEEEE",
)
