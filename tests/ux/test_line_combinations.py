"""Cross-stage option combination tests for the line command.

All combinations work correctly — these tests lock in correct behavior.
"""

from __future__ import annotations

from pathlib import Path

from tests.ux.conftest import invoke


class TestLineCrossStage:
    """Interactions between line options at different pipeline stages."""

    def test_color_plus_head(self, ux_line_csv: Path) -> None:
        """--color + --head: color grouping with limited rows."""
        result = invoke(
            "line", "-f", str(ux_line_csv),
            "--x", "date", "--y", "temp",
            "--color", "region", "--head", "6",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # First 6 rows are all north region
        assert "north" in result.stdout

    def test_where_plus_color(self, ux_line_csv: Path) -> None:
        """--where + --color: filter then group by color."""
        result = invoke(
            "line", "-f", str(ux_line_csv),
            "--x", "date", "--y", "temp",
            "--where", "region=south",
            "--color", "region",
            "--format", "compact",
        )
        assert result.exit_code == 0
        assert "south" in result.stdout
        # north should not appear (filtered out)
        assert "north" not in result.stdout

    def test_head_plus_where(self, ux_line_csv: Path) -> None:
        """--head + --where: head limits rows, where filters from those."""
        result = invoke(
            "line", "-f", str(ux_line_csv),
            "--x", "date", "--y", "temp",
            "--head", "8", "--where", "region=north",
            "--format", "compact",
        )
        assert result.exit_code == 0

    def test_multi_y_plus_color(self, ux_line_csv: Path) -> None:
        """Multiple --y + --color: multiple series per color group."""
        result = invoke(
            "line", "-f", str(ux_line_csv),
            "--x", "date",
            "--y", "temp", "--y", "humidity",
            "--color", "region",
            "--format", "compact",
        )
        assert result.exit_code == 0
        assert "north" in result.stdout
        assert "south" in result.stdout
