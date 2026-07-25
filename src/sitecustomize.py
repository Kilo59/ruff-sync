"""Process startup script to alias httpx to httpx2 before pytest plugins load."""

from __future__ import annotations

import httpx2 as httpx

httpx.alias_httpx()
