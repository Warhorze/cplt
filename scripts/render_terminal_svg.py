#!/usr/bin/env python3
"""Render plain terminal text output into a dark-themed SVG image."""

from __future__ import annotations

import argparse
import html
from pathlib import Path


def render_svg(text: str, title: str) -> str:
    lines = text.splitlines() or [""]
    max_chars = max(len(line) for line in lines)

    char_width = 8.4
    line_height = 20
    pad_x = 18
    pad_top = 42
    pad_bottom = 18

    width = int((max_chars * char_width) + (pad_x * 2))
    height = int((len(lines) * line_height) + pad_top + pad_bottom)

    out_lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        "  <defs>",
        "    <style>",
        "      .bg { fill: #0f1117; }",
        "      .title { fill: #9aa4b2; font: 600 13px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }",
        "      .code { fill: #e6edf3; font: 14px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; white-space: pre; }",
        "    </style>",
        "  </defs>",
        f'  <rect class="bg" x="0" y="0" width="{width}" height="{height}" rx="8" />',
        '  <text class="title" x="18" y="24">csvplot output</text>',
    ]

    y = pad_top
    for line in lines:
        escaped = html.escape(line)
        out_lines.append(f'  <text class="code" x="{pad_x}" y="{y}">{escaped}</text>')
        y += line_height

    out_lines.append("</svg>")
    out_lines.append("")
    return "\n".join(out_lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input text file")
    parser.add_argument("output", type=Path, help="Output SVG path")
    parser.add_argument("--title", default="csvplot output", help="SVG aria-label title")
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    svg = render_svg(text, args.title)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
