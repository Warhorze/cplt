"""Tests for the unified color theme module."""

from cplt.theme import RAINBOW_PALETTE, hex_color, rgb_color


def test_palette_has_ten_entries():
    assert len(RAINBOW_PALETTE) == 10


def test_hex_color_format():
    h = hex_color(0)
    assert h == "#dcdcaa"
    assert h.startswith("#")
    assert len(h) == 7


def test_hex_color_wraps():
    assert hex_color(0) == hex_color(10)
    assert hex_color(3) == hex_color(13)


def test_rgb_color_returns_tuple():
    assert rgb_color(0) == (220, 220, 170)


def test_rgb_color_wraps():
    assert rgb_color(0) == rgb_color(10)
