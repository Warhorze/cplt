"""ANSI text → PNG image renderer using Pillow."""

from __future__ import annotations

import re
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

# Theme defaults
_BG = (0x1E, 0x1E, 0x1E)
_FG = (0xCC, 0xCC, 0xCC)
_PADDING = 16

# Standard 16 ANSI colors (normal 0-7, bright 8-15)
_ANSI_16: list[tuple[int, int, int]] = [
    (0, 0, 0),  # 0 black
    (205, 49, 49),  # 1 red
    (13, 188, 121),  # 2 green
    (229, 229, 16),  # 3 yellow
    (36, 114, 200),  # 4 blue
    (188, 63, 188),  # 5 magenta
    (17, 168, 205),  # 6 cyan
    (204, 204, 204),  # 7 white
    (102, 102, 102),  # 8 bright black
    (241, 76, 76),  # 9 bright red
    (35, 209, 139),  # 10 bright green
    (245, 245, 67),  # 11 bright yellow
    (59, 142, 234),  # 12 bright blue
    (214, 112, 214),  # 13 bright magenta
    (41, 184, 219),  # 14 bright cyan
    (242, 242, 242),  # 15 bright white
]

# SGR escape pattern
_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")

# Braille range U+2800–U+28FF
_BRAILLE_START = 0x2800
_BRAILLE_END = 0x28FF

# Braille dot positions: bit index → (col, row) in a 2×4 grid
_BRAILLE_DOT_MAP: dict[int, tuple[int, int]] = {
    0: (0, 0),
    1: (0, 1),
    2: (0, 2),
    3: (1, 0),
    4: (1, 1),
    5: (1, 2),
    6: (0, 3),
    7: (1, 3),
}


def _color_256(n: int) -> tuple[int, int, int]:
    """Convert a 256-color index to RGB."""
    if n < 16:
        return _ANSI_16[n]
    if n < 232:
        n -= 16
        r = (n // 36) * 51
        g = ((n % 36) // 6) * 51
        b = (n % 6) * 51
        return (r, g, b)
    # Grayscale 232-255
    g = 8 + (n - 232) * 10
    return (g, g, g)


@dataclass
class Cell:
    """A single character cell with foreground/background colors."""

    char: str
    fg: tuple[int, int, int] | None = None  # None = default
    bg: tuple[int, int, int] | None = None  # None = default
    bold: bool = False


def parse_ansi(text: str) -> list[list[Cell]]:
    """Parse ANSI-escaped text into a grid of Cell rows.

    Returns a list of rows, each row a list of Cells.
    When called from tests expecting a flat list for single-line input,
    the result can be indexed as rows[0].
    """
    rows: list[list[Cell]] = [[]]
    fg: tuple[int, int, int] | None = None
    bg: tuple[int, int, int] | None = None
    bold = False

    pos = 0
    while pos < len(text):
        m = _SGR_RE.match(text, pos)
        if m:
            params_str = m.group(1)
            params = [int(p) if p else 0 for p in params_str.split(";")]
            i = 0
            while i < len(params):
                p = params[i]
                if p == 0:
                    fg, bg, bold = None, None, False
                elif p == 1:
                    bold = True
                    # Bold → bright mapping for basic colors
                    if fg is not None:
                        for idx in range(8):
                            if fg == _ANSI_16[idx]:
                                fg = _ANSI_16[idx + 8]
                                break
                elif 30 <= p <= 37:
                    idx = p - 30
                    fg = _ANSI_16[idx + 8] if bold else _ANSI_16[idx]
                elif 40 <= p <= 47:
                    bg = _ANSI_16[p - 40]
                elif 90 <= p <= 97:
                    fg = _ANSI_16[p - 90 + 8]
                elif 100 <= p <= 107:
                    bg = _ANSI_16[p - 100 + 8]
                elif p == 38 and i + 1 < len(params):
                    if params[i + 1] == 5 and i + 2 < len(params):
                        fg = _color_256(params[i + 2])
                        i += 2
                    elif params[i + 1] == 2 and i + 4 < len(params):
                        fg = (params[i + 2], params[i + 3], params[i + 4])
                        i += 4
                elif p == 48 and i + 1 < len(params):
                    if params[i + 1] == 5 and i + 2 < len(params):
                        bg = _color_256(params[i + 2])
                        i += 2
                    elif params[i + 1] == 2 and i + 4 < len(params):
                        bg = (params[i + 2], params[i + 3], params[i + 4])
                        i += 4
                i += 1
            pos = m.end()
        elif text[pos] == "\n":
            rows.append([])
            pos += 1
        else:
            rows[-1].append(Cell(char=text[pos], fg=fg, bg=bg, bold=bold))
            pos += 1

    return rows


def _is_braille(ch: str) -> bool:
    cp = ord(ch)
    return _BRAILLE_START <= cp <= _BRAILLE_END


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try monospace fonts in order, fall back to default."""
    names = [
        "DejaVuSansMono.ttf",
        "DejaVu Sans Mono",
        "LiberationMono-Regular.ttf",
        "Consolas",
        "Courier New",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def export_png(ansi_text: str, out_path: str, font_size: int = 16) -> None:
    """Render ANSI-escaped text to a PNG file."""
    supersample = 2
    render_size = font_size * supersample

    font = _load_font(render_size)
    cell_w = int(font.getlength("M"))
    # Line height: ascent + descent with a small buffer
    bbox = font.getbbox("Mj|")
    cell_h = int(bbox[3] - bbox[1]) + 2

    rows = parse_ansi(ansi_text)

    max_cols = max((len(row) for row in rows), default=0)
    n_rows = len(rows)

    padding = _PADDING * supersample
    img_w = max_cols * cell_w + 2 * padding
    img_h = n_rows * cell_h + 2 * padding

    img = Image.new("RGB", (img_w, img_h), _BG)
    draw = ImageDraw.Draw(img)

    # Braille rendering parameters
    br_r = 0.25 * cell_w
    br_mx = 0.10 * cell_w
    br_my = 0.04 * cell_h

    for row_idx, row in enumerate(rows):
        for col_idx, cell in enumerate(row):
            x = padding + col_idx * cell_w
            y = padding + row_idx * cell_h

            fg = cell.fg or _FG
            cell_bg = cell.bg

            # Draw background if set
            if cell_bg:
                draw.rectangle([x, y, x + cell_w, y + cell_h], fill=cell_bg)

            ch = cell.char
            if _is_braille(ch):
                _draw_braille(draw, ch, x, y, cell_w, cell_h, fg, br_r, br_mx, br_my)
            else:
                glyph_w = font.getlength(ch)
                offset = (cell_w - glyph_w) / 2
                draw.text((x + offset, y), ch, font=font, fill=fg)

    # Downscale with LANCZOS
    final_w = img_w // supersample
    final_h = img_h // supersample
    img = img.resize((final_w, final_h), Image.Resampling.LANCZOS)
    img.save(out_path, "PNG")


def _draw_braille(
    draw: ImageDraw.ImageDraw,
    ch: str,
    x: float,
    y: float,
    cell_w: int,
    cell_h: int,
    fg: tuple[int, int, int],
    r: float,
    mx: float,
    my: float,
) -> None:
    """Render a braille character as programmatic dots."""
    bits = ord(ch) - _BRAILLE_START
    # Grid spacing for 2 columns × 4 rows
    col_spacing = (cell_w - 2 * mx) / 1  # 2 columns, 1 gap
    row_spacing = (cell_h - 2 * my) / 3  # 4 rows, 3 gaps

    for bit_idx, (col, row) in _BRAILLE_DOT_MAP.items():
        if bits & (1 << bit_idx):
            cx = x + mx + col * col_spacing
            cy = y + my + row * row_spacing
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fg)
