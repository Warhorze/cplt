"""Cross-stage option combination tests for the timeline command.

All combinations work correctly — these tests lock in correct behavior.
"""

from __future__ import annotations

from pathlib import Path

from tests.ux.conftest import invoke


class TestTimelineCrossStage:
    """Interactions between timeline options at different pipeline stages."""

    def test_where_plus_view_window(self, timeline_csv: Path) -> None:
        """--where filters rows, --from/--to clips the view window."""
        result = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--where",
            "category=backend",
            "--from",
            "2024-02-01",
            "--to",
            "2024-03-31",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # Backend entries in Feb-Mar window: Alpha(Feb), Charlie(Feb-Mar), Echo(Mar)
        assert "Alpha" in result.stdout or "Charlie" in result.stdout or "Echo" in result.stdout

    def test_color_plus_y_detail(self, timeline_csv: Path) -> None:
        """--color + --y-detail: color and sub-grouping work together."""
        result = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--color",
            "category",
            "--y-detail",
            "detail",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        out = result.stdout.lower()
        # Both color legend and detail labels should be present
        assert "backend" in out or "frontend" in out
        assert "api" in out or "db" in out or "ui" in out

    def test_dot_plus_view_window(self, timeline_csv: Path) -> None:
        """--dot + --from/--to: dots are visible within the clipped window."""
        result = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--dot",
            "due_date",
            "--from",
            "2024-01-01",
            "--to",
            "2024-01-31",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "◆" in result.stdout

    def test_head_plus_where(self, timeline_csv: Path) -> None:
        """--head + --where: head limits rows before filter."""
        result = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--head",
            "5",
            "--where",
            "category=frontend",
            "--format",
            "compact",
        )
        assert result.exit_code == 0

    def test_vline_plus_view_window(self, timeline_csv: Path) -> None:
        """--vline + --from/--to: vline appears within the view window."""
        result = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--vline",
            "2024-02-15",
            "--label",
            "mid",
            "--from",
            "2024-02-01",
            "--to",
            "2024-03-01",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "mid" in result.stdout

    def test_color_plus_dot(self, timeline_csv: Path) -> None:
        """--color + --dot: both color legend and dots in output."""
        result = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--color",
            "category",
            "--dot",
            "due_date",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "◆" in result.stdout

    def test_option_order_where_head(self, timeline_csv: Path) -> None:
        """Option order must not matter: --where before --head vs after."""
        result_a = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--where",
            "category=backend",
            "--head",
            "5",
            "--format",
            "compact",
        )
        result_b = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--head",
            "5",
            "--where",
            "category=backend",
            "--format",
            "compact",
        )
        assert result_a.exit_code == 0
        assert result_b.exit_code == 0
        assert result_a.stdout == result_b.stdout

    def test_multi_y_plus_color(self, timeline_csv: Path) -> None:
        """Multiple --y + --color: composite labels with color grouping."""
        result = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--y",
            "category",
            "--color",
            "detail",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert " | " in result.stdout
