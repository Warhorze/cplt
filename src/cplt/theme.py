"""Canonical color palette shared across all output formats."""

from __future__ import annotations

# VS Code / Rainbow CSV inspired palette (RGB tuples).
RAINBOW_PALETTE: list[tuple[int, int, int]] = [
    (220, 220, 170),  # #DCDCAA — soft yellow
    (206, 145, 120),  # #CE9178 — warm orange
    (78, 201, 176),  # #4EC9B0 — teal
    (86, 156, 214),  # #569CD6 — blue
    (197, 134, 192),  # #C586C0 — purple
    (156, 220, 254),  # #9CDCFE — light blue
    (215, 186, 125),  # #D7BA7D — gold
    (181, 206, 168),  # #B5CEA8 — sage green
    (244, 71, 71),  # #F44747 — red
    (96, 139, 78),  # #608B4E — forest green
]


def hex_color(idx: int) -> str:
    """Return '#RRGGBB' for Rich markup at palette index."""
    r, g, b = RAINBOW_PALETTE[idx % len(RAINBOW_PALETTE)]
    return f"#{r:02x}{g:02x}{b:02x}"


def rgb_color(idx: int) -> tuple[int, int, int]:
    """Return RGB tuple for plotext at palette index."""
    return RAINBOW_PALETTE[idx % len(RAINBOW_PALETTE)]
