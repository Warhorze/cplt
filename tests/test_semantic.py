"""Tests for semantic format — visual layout without ANSI codes."""

from __future__ import annotations

import re

from rich.table import Table

from cplt.semantic import semantic_rich, strip_ansi

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class TestStripAnsi:
    def test_removes_color_codes(self):
        text = "\x1b[31mred\x1b[0m normal"
        assert strip_ansi(text) == "red normal"

    def test_preserves_plain_text(self):
        text = "hello world"
        assert strip_ansi(text) == "hello world"

    def test_preserves_box_drawing(self):
        text = "\x1b[0m┌──────┐\x1b[0m"
        result = strip_ansi(text)
        assert "┌──────┐" in result
        assert "\x1b" not in result

    def test_preserves_braille(self):
        text = "\x1b[38;5;1m⣿⡇\x1b[0m"
        result = strip_ansi(text)
        assert "⣿⡇" in result
        assert "\x1b" not in result

    def test_empty_string(self):
        assert strip_ansi("") == ""


class TestSemanticRich:
    def test_table_preserves_structure(self):
        """Rich table renders with box-drawing chars but no ANSI."""
        table = Table(title="Test")
        table.add_column("Name")
        table.add_column("Value")
        table.add_row("Alice", "100")
        out = semantic_rich(table)
        assert "Test" in out
        assert "Name" in out
        assert "Alice" in out
        assert "100" in out
        # Box-drawing preserved
        assert "┃" in out or "│" in out
        # No ANSI codes
        assert not _ANSI_RE.search(out)

    def test_styled_markup_stripped(self):
        """Rich markup like [bold] and [green] is stripped."""
        table = Table()
        table.add_column("X")
        table.add_row("[green]●[/green]")
        out = semantic_rich(table)
        assert "●" in out
        assert "[green]" not in out
        assert not _ANSI_RE.search(out)

    def test_multiple_renderables(self):
        """Multiple tables are concatenated."""
        t1 = Table(title="Table One")
        t1.add_column("Col A")
        t1.add_row("val1")
        t2 = Table(title="Table Two")
        t2.add_column("Col B")
        t2.add_row("val2")
        out = semantic_rich(t1, t2)
        assert "Table One" in out
        assert "Table Two" in out
        assert "val1" in out
        assert "val2" in out
        assert not _ANSI_RE.search(out)


class TestSemanticPlotextOutput:
    def test_build_returns_plain_chart(self):
        """plt.build() + strip_ansi produces readable chart without ANSI."""
        import plotext as plt

        plt.clear_figure()
        plt.plot([1, 2, 3], [1, 2, 3])
        plt.title("test chart")
        canvas = plt.build()
        result = strip_ansi(canvas)
        assert "test chart" in result
        assert not _ANSI_RE.search(result)
        # Box-drawing from plotext preserved
        assert "┌" in result or "└" in result

    def test_no_ansi_in_bar_build(self):
        """Bar chart build output has no ANSI after stripping."""
        import plotext as plt

        plt.clear_figure()
        plt.bar(["A", "B"], [10, 20])
        plt.title("bar test")
        canvas = plt.build()
        result = strip_ansi(canvas)
        assert "bar test" in result
        assert not _ANSI_RE.search(result)
