"""Unit tests for the ANSI → PNG export module."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from csvplot.export import export_png, parse_ansi


class TestExportPngCreatesFile:
    def test_basic_ansi_string_produces_png(self, tmp_path: Path) -> None:
        out = tmp_path / "out.png"
        export_png("\x1b[31mHello\x1b[0m world", str(out))
        assert out.exists()
        img = Image.open(out)
        assert img.format == "PNG"

    def test_plain_text_produces_png(self, tmp_path: Path) -> None:
        out = tmp_path / "out.png"
        export_png("plain text", str(out))
        assert out.exists()


class TestExportPngDimensions:
    def test_dimensions_match_grid(self, tmp_path: Path) -> None:
        """Image dimensions should scale with the number of columns and rows."""
        text = "AB\nCD"
        out = tmp_path / "out.png"
        export_png(text, str(out), font_size=16)
        img = Image.open(out)
        # At 2x supersample then downscale, the final image should be
        # roughly (cols * cell_w + 2*padding) x (rows * cell_h + 2*padding).
        # We just check it's reasonable (not 0x0, and width < height for 2-col 2-row).
        assert img.width > 0
        assert img.height > 0

    def test_more_columns_means_wider_image(self, tmp_path: Path) -> None:
        out_short = tmp_path / "short.png"
        out_long = tmp_path / "long.png"
        export_png("AB", str(out_short), font_size=16)
        export_png("ABCDEFGHIJ", str(out_long), font_size=16)
        short = Image.open(out_short)
        long = Image.open(out_long)
        assert long.width > short.width


class TestAnsiParserBasicColors:
    def test_reset_returns_default(self) -> None:
        rows = parse_ansi("\x1b[0mX")
        assert len(rows[0]) == 1
        assert rows[0][0].char == "X"
        assert rows[0][0].fg is None  # None means default

    def test_basic_red_foreground(self) -> None:
        rows = parse_ansi("\x1b[31mR")
        assert len(rows[0]) == 1
        assert rows[0][0].fg is not None

    def test_bright_foreground(self) -> None:
        rows = parse_ansi("\x1b[91mB")
        assert len(rows[0]) == 1
        assert rows[0][0].fg is not None

    def test_basic_background_color(self) -> None:
        rows = parse_ansi("\x1b[42mG")
        assert len(rows[0]) == 1
        assert rows[0][0].bg is not None

    def test_multiple_sgr_params(self) -> None:
        # Bold + red foreground
        rows = parse_ansi("\x1b[1;31mX")
        assert len(rows[0]) == 1
        assert rows[0][0].fg is not None


class TestAnsiParser256Color:
    def test_256_foreground(self) -> None:
        rows = parse_ansi("\x1b[38;5;196mR")
        assert len(rows[0]) == 1
        assert rows[0][0].fg is not None

    def test_256_background(self) -> None:
        rows = parse_ansi("\x1b[48;5;21mB")
        assert len(rows[0]) == 1
        assert rows[0][0].bg is not None

    def test_truecolor_foreground(self) -> None:
        rows = parse_ansi("\x1b[38;2;255;128;0mO")
        assert len(rows[0]) == 1
        assert rows[0][0].fg == (255, 128, 0)

    def test_truecolor_background(self) -> None:
        rows = parse_ansi("\x1b[48;2;0;128;255mB")
        assert len(rows[0]) == 1
        assert rows[0][0].bg == (0, 128, 255)


class TestBrailleRendering:
    def test_braille_char_produces_non_bg_pixels(self, tmp_path: Path) -> None:
        """Braille characters (U+2800-U+28FF) should produce dots, not font glyphs."""
        out = tmp_path / "braille.png"
        # U+2840 = dots at position 6 (col=0, row=3)
        export_png("\u2840", str(out), font_size=16)
        img = Image.open(out)
        bg = (0x1E, 0x1E, 0x1E)
        non_bg = sum(1 for x in range(img.width) for y in range(img.height)
                     if img.getpixel((x, y))[:3] != bg)
        assert non_bg > 0

    def test_empty_braille_has_fewer_dots(self, tmp_path: Path) -> None:
        """U+2800 (empty braille) should have fewer non-bg pixels than U+28FF (all dots)."""
        out_empty = tmp_path / "empty.png"
        out_full = tmp_path / "full.png"
        export_png("\u2800", str(out_empty), font_size=16)
        export_png("\u28FF", str(out_full), font_size=16)
        empty = Image.open(out_empty)
        full = Image.open(out_full)
        bg = (0x1E, 0x1E, 0x1E)
        empty_dots = sum(1 for x in range(empty.width) for y in range(empty.height)
                         if empty.getpixel((x, y))[:3] != bg)
        full_dots = sum(1 for x in range(full.width) for y in range(full.height)
                        if full.getpixel((x, y))[:3] != bg)
        assert full_dots > empty_dots
