#!/usr/bin/env python3
"""Render plain terminal text output into a dark-themed PNG image."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        "/Library/Fonts/Menlo.ttc",
        "C:\\Windows\\Fonts\\consola.ttf",
    ]
    for path in candidates:
        p = Path(path)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def text_size(font: ImageFont.ImageFont, text: str) -> tuple[int, int]:
    left, top, right, bottom = font.getbbox(text)
    return right - left, bottom - top


def render_png(text: str, output: Path) -> None:
    lines = text.splitlines() or [""]
    code_font = load_font(18)
    title_font = load_font(14)

    sample_w, sample_h = text_size(code_font, "M")
    char_w = max(sample_w, 10)
    line_h = max(sample_h + 5, 22)
    max_chars = max(len(line) for line in lines)

    pad_x = 24
    pad_top = 52
    pad_bottom = 22
    width = (max_chars * char_w) + (pad_x * 2)
    height = (len(lines) * line_h) + pad_top + pad_bottom

    img = Image.new("RGB", (width, height), "#0f1117")
    draw = ImageDraw.Draw(img)
    draw.text((24, 18), "csvplot output", font=title_font, fill="#9aa4b2")

    y = pad_top
    for line in lines:
        draw.text((pad_x, y), line, font=code_font, fill="#e6edf3")
        y += line_h

    output.parent.mkdir(parents=True, exist_ok=True)
    img.save(output, format="PNG", optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input text file")
    parser.add_argument("output", type=Path, help="Output PNG path")
    parser.add_argument(
        "--title",
        default="csvplot output",
        help="Compatibility flag; currently not rendered in PNG output.",
    )
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    render_png(text, args.output)


if __name__ == "__main__":
    main()
