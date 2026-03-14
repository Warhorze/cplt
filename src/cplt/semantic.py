"""Semantic format — visual layout without ANSI color codes."""

from __future__ import annotations

import io
import re
from typing import Any

from rich.console import Console

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from a string."""
    return _ANSI_RE.sub("", text)


def semantic_rich(*renderables: Any, width: int = 120) -> str:
    """Capture Rich renderables as plain text with layout preserved."""
    console = Console(record=True, width=width, file=io.StringIO())
    for r in renderables:
        console.print(r)
    return console.export_text(styles=False)
