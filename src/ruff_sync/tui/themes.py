"""Custom themes for the ruff-sync TUI."""

from __future__ import annotations

from textual.theme import Theme

# AMBER_EMBER
# High-contrast, warm dark theme with vibrant gold primary colors.
AMBER_EMBER = Theme(
    name="amber-ember",
    primary="#FFB300",  # Darker, punchy Amber
    secondary="#FFD54F",  # Lighter Amber
    accent="#D81B60",  # Material Magenta
    warning="#FFD600",  # Vibrant Yellow (A700) for distinct Warning/Ignored status
    error="#E91E63",  # Pink 500
    success="#81C784",  # Light Green 300
    background="#121212",  # Material Dark
    surface="#1E1E1E",
    panel="#2C2C2C",
    boost="#2C2C2C",
    dark=True,
)
