"""Constants for the Ruff-Sync Terminal User Interface."""

from __future__ import annotations

import re
from typing import Final

# Regex pattern for matching Ruff rule codes (e.g., E501, RUF012)
RULE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[A-Z]+[0-9]+$")
