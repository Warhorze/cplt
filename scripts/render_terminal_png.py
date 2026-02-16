#!/usr/bin/env python3
"""Render terminal text output (including ANSI colors) into a dark-themed PNG image."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")
DEFAULT_FG = "#e6edf3"
ANSI_BASE_COLORS = {
    30: "#0f1117",
    31: "#ff6b6b",
    32: "#50d890",
    33: "#ffd166",
    34: "#74c0fc",
    35: "#c77dff",
    36: "#64dfdf",
    37: "#f1f3f5",
    90: "#6c757d",
    91: "#ff8787",
    92: "#69db7c",
    93: "#ffe066",
    94: "#91a7ff",
    95: "#da77f2",
    96: "#66d9e8",
    97: "#ffffff",
}


def xterm_256_to_hex(index: int) -> str:
    if index < 0:
        index = 0
    if index > 255:
        index = 255

    basic = [
        "#000000",
        "#800000",
        "#008000",
        "#808000",
        "#000080",
        "#800080",
        "#008080",
        "#c0c0c0",
        "#808080",
        "#ff0000",
        "#00ff00",
        "#ffff00",
        "#0000ff",
        "#ff00ff",
        "#00ffff",
        "#ffffff",
    ]
    if index < 16:
        return basic[index]

    if index < 232:
        i = index - 16
        r = i // 36
        g = (i % 36) // 6
        b = i % 6
        levels = [0, 95, 135, 175, 215, 255]
        return f"#{levels[r]:02x}{levels[g]:02x}{levels[b]:02x}"

    gray = 8 + (index - 232) * 10
    return f"#{gray:02x}{gray:02x}{gray:02x}"


def normalize_codes(raw_codes: str) -> list[int]:
    if raw_codes == "":
        return [0]
    out: list[int] = []
    for part in raw_codes.split(";"):
        if part == "":
            out.append(0)
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out or [0]


def apply_codes(codes: list[int], current_fg: str) -> str:
    fg = current_fg
    i = 0
    while i < len(codes):
        code = codes[i]
        if code == 0 or code == 39:
            fg = DEFAULT_FG
        elif code in ANSI_BASE_COLORS:
            fg = ANSI_BASE_COLORS[code]
        elif code == 38:
            if i + 1 < len(codes) and codes[i + 1] == 5 and i + 2 < len(codes):
                fg = xterm_256_to_hex(codes[i + 2])
                i += 2
            elif i + 1 < len(codes) and codes[i + 1] == 2 and i + 4 < len(codes):
                r = max(0, min(255, codes[i + 2]))
                g = max(0, min(255, codes[i + 3]))
                b = max(0, min(255, codes[i + 4]))
                fg = f"#{r:02x}{g:02x}{b:02x}"
                i += 4
        i += 1
    return fg


def parse_ansi_line(line: str) -> list[tuple[str, str]]:
    segments: list[tuple[str, str]] = []
    cursor = 0
    fg = DEFAULT_FG

    for match in ANSI_RE.finditer(line):
        start, end = match.span()
        if start > cursor:
            text = line[cursor:start]
            if text:
                segments.append((text, fg))
        codes = normalize_codes(match.group(1))
        fg = apply_codes(codes, fg)
        cursor = end

    if cursor < len(line):
        tail = line[cursor:]
        if tail:
            segments.append((tail, fg))

    if not segments:
        segments.append(("", DEFAULT_FG))
    return segments


def visible_line_length(line: str) -> int:
    clean = ANSI_RE.sub("", line)
    return len(clean)


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


def render_png(text: str, output: Path, title: str) -> None:
    lines = text.splitlines() or [""]
    code_font = load_font(18)
    title_font = load_font(14)

    sample_w, sample_h = text_size(code_font, "M")
    char_w = max(sample_w, 10)
    line_h = max(sample_h + 5, 22)
    max_chars = max(visible_line_length(line) for line in lines)

    pad_x = 24
    pad_top = 52
    pad_bottom = 22
    width = (max_chars * char_w) + (pad_x * 2)
    height = (len(lines) * line_h) + pad_top + pad_bottom

    img = Image.new("RGB", (width, height), "#0f1117")
    draw = ImageDraw.Draw(img)
    draw.text((24, 18), title, font=title_font, fill="#9aa4b2")

    y = pad_top
    for line in lines:
        x = pad_x
        for segment, color in parse_ansi_line(line):
            if segment:
                draw.text((x, y), segment, font=code_font, fill=color)
                seg_w, _ = text_size(code_font, segment)
                x += seg_w
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
        help="Title rendered in the image header.",
    )
    args = parser.parse_args()

    text = args.input.read_text(encoding="utf-8")
    render_png(text, args.output, args.title)


if __name__ == "__main__":
    main()
