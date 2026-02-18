"""Per-command option behavior tests.

All content assertions use --format compact output (stable, machine-readable).
Visual/semantic only used for exit-code checks where relevant.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.ux.conftest import invoke

# ============================================================================
# Timeline option tests
# ============================================================================


class TestTimelineOptions:
    def test_multi_layer(self, timeline_csv: Path) -> None:
        """2 --x pairs produce rows with distinct layer characters (█ vs #)."""
        result = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # Multi-layer renders each label twice: once with █ (layer 0) and # (layer 1).
        assert "█" in result.stdout
        assert "#" in result.stdout

    def test_vline(self, timeline_csv: Path) -> None:
        """--vline and --label appear in compact output."""
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
            "deadline",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "deadline" in result.stdout

    def test_view_window(self, timeline_csv: Path) -> None:
        """--from / --to clips output to the specified date range."""
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
            "--from",
            "2024-02-01",
            "--to",
            "2024-02-28",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # Alpha's second segment (Feb) and Bravo (ends Jan 25) should be visible
        # but segments fully outside the window should be clipped.
        assert "2024-02" in result.stdout

    def test_y_detail(self, timeline_csv: Path) -> None:
        """--y-detail creates sub-grouped labels."""
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
            "--y-detail",
            "detail",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # y-detail should add the detail value to the label
        assert "api" in result.stdout or "db" in result.stdout

    def test_no_open_end(self, timeline_csv: Path) -> None:
        """--no-open-end excludes rows with null end dates."""
        result_with = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--format",
            "compact",
        )
        result_without = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--no-open-end",
            "--format",
            "compact",
        )
        assert result_with.exit_code == 0
        assert result_without.exit_code == 0
        # Echo has null end; with open-end it appears, without it doesn't.
        assert "Echo" in result_with.stdout
        assert "Echo" not in result_without.stdout

    def test_color(self, timeline_csv: Path) -> None:
        """--color segments by column value."""
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
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # Color legend should appear in compact output.
        out = result.stdout.lower()
        assert "backend" in out or "frontend" in out or "data" in out

    def test_txt_visual(self, timeline_csv: Path) -> None:
        """--txt with visual format exits cleanly."""
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
            "--txt",
            "label",
            "--format",
            "visual",
        )
        assert result.exit_code == 0

    def test_txt_compact_is_noop(self, timeline_csv: Path) -> None:
        """--txt has no effect in compact format (feedback #8)."""
        base = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--format",
            "compact",
        )
        with_txt = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--txt",
            "label",
            "--format",
            "compact",
        )
        assert base.exit_code == 0
        assert with_txt.exit_code == 0
        assert base.stdout == with_txt.stdout

    def test_multi_y(self, timeline_csv: Path) -> None:
        """Multiple --y values form composite labels."""
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
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # Composite labels join with " | "
        assert " | " in result.stdout

    def test_dot(self, timeline_csv: Path) -> None:
        """--dot renders dot markers in compact output."""
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
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "◆" in result.stdout
        assert "due_date" in result.stdout

    def test_title(self, timeline_csv: Path) -> None:
        """--title appears in output."""
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
            "--title",
            "My Timeline",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "My Timeline" in result.stdout


# ============================================================================
# Bar option tests
# ============================================================================


class TestBarOptions:
    def test_sort_label(self, ux_bar_csv: Path) -> None:
        """--sort label produces alphabetical order."""
        result = invoke(
            "bar",
            "-f",
            str(ux_bar_csv),
            "-c",
            "status",
            "--sort",
            "label",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        lines = [ln for ln in result.stdout.split("\n") if ln.strip()]
        # Find lines with status labels and verify alphabetical order.
        labels = []
        for line in lines:
            for status in ("blocked", "closed", "in_progress", "open"):
                if status in line:
                    labels.append(status)
                    break
        assert labels == sorted(labels), f"Not alphabetical: {labels}"

    def test_top(self, ux_bar_csv: Path) -> None:
        """--top 2 shows only the 2 highest-count categories."""
        result = invoke(
            "bar",
            "-f",
            str(ux_bar_csv),
            "-c",
            "status",
            "--top",
            "2",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # open=4, blocked=3, closed=3, in_progress=2 → top 2 should be open + one of blocked/closed
        # Just verify we have at most 2 categories shown.
        lines = result.stdout.strip().split("\n")
        statuses = ("open", "closed", "blocked", "in_progress")
        data_lines = [ln for ln in lines if any(s in ln for s in statuses)]
        assert len(data_lines) <= 2

    def test_horizontal_visual(self, ux_bar_csv: Path) -> None:
        """--horizontal with visual format exits cleanly."""
        result = invoke(
            "bar",
            "-f",
            str(ux_bar_csv),
            "-c",
            "status",
            "--horizontal",
            "--format",
            "visual",
        )
        assert result.exit_code == 0

    def test_horizontal_compact_is_noop(self, ux_bar_csv: Path) -> None:
        """--horizontal has no effect in compact format (feedback #9)."""
        base = invoke(
            "bar",
            "-f",
            str(ux_bar_csv),
            "-c",
            "status",
            "--format",
            "compact",
        )
        horiz = invoke(
            "bar",
            "-f",
            str(ux_bar_csv),
            "-c",
            "status",
            "--horizontal",
            "--format",
            "compact",
        )
        assert base.exit_code == 0
        assert horiz.exit_code == 0
        assert base.stdout == horiz.stdout

    def test_title(self, ux_bar_csv: Path) -> None:
        """--title appears in output."""
        result = invoke(
            "bar",
            "-f",
            str(ux_bar_csv),
            "-c",
            "status",
            "--title",
            "Status Report",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "Status Report" in result.stdout


# ============================================================================
# Line option tests
# ============================================================================


class TestLineOptions:
    def test_multi_y(self, ux_line_csv: Path) -> None:
        """2 --y columns produce 2 series in compact output."""
        result = invoke(
            "line",
            "-f",
            str(ux_line_csv),
            "--x",
            "date",
            "--y",
            "temp",
            "--y",
            "humidity",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "temp" in result.stdout
        assert "humidity" in result.stdout

    def test_color_grouping(self, ux_line_csv: Path) -> None:
        """--color region splits series into groups."""
        result = invoke(
            "line",
            "-f",
            str(ux_line_csv),
            "--x",
            "date",
            "--y",
            "temp",
            "--color",
            "region",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "north" in result.stdout
        assert "south" in result.stdout

    def test_compact_decimal_precision(self, ux_line_csv: Path) -> None:
        """Compact line min/max values should not have excessive decimals (feedback #7)."""
        result = invoke(
            "line",
            "-f",
            str(ux_line_csv),
            "--x",
            "date",
            "--y",
            "temp",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # Find all decimal numbers in the output.
        decimals = re.findall(r"\d+\.(\d+)", result.stdout)
        for frac in decimals:
            assert len(frac) <= 4, (
                f"Excessive decimal precision ({len(frac)} places) in compact output:\n"
                f"{result.stdout}"
            )

    def test_title(self, ux_line_csv: Path) -> None:
        """--title appears in output."""
        result = invoke(
            "line",
            "-f",
            str(ux_line_csv),
            "--x",
            "date",
            "--y",
            "temp",
            "--title",
            "Temperature",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "Temperature" in result.stdout


# ============================================================================
# Bubble option tests
# ============================================================================


class TestBubbleOptions:
    def test_color_changes_output(self, ux_bubble_csv: Path) -> None:
        """--color category changes the output compared to without --color."""
        base = invoke(
            "bubble",
            "-f",
            str(ux_bubble_csv),
            "--cols",
            "feat_a",
            "--cols",
            "feat_b",
            "--y",
            "name",
            "--format",
            "visual",
        )
        colored = invoke(
            "bubble",
            "-f",
            str(ux_bubble_csv),
            "--cols",
            "feat_a",
            "--cols",
            "feat_b",
            "--y",
            "name",
            "--color",
            "category",
            "--format",
            "visual",
        )
        assert base.exit_code == 0
        assert colored.exit_code == 0
        assert base.stdout != colored.stdout
        assert "Legend" in colored.stdout

    def test_top_fill_rate(self, ux_bubble_csv: Path) -> None:
        """--top 2 selects the 2 most-filled columns."""
        result = invoke(
            "bubble",
            "-f",
            str(ux_bubble_csv),
            "--cols",
            "feat_a",
            "--cols",
            "feat_b",
            "--cols",
            "feat_c",
            "--y",
            "name",
            "--top",
            "2",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # Should only show 2 of the 3 feature columns.
        out = result.stdout

        # Count how many of feat_a, feat_b, feat_c appear as column headers.
        cols_present = sum(1 for c in ("feat_a", "feat_b", "feat_c") if c in out)
        assert cols_present <= 2

    def test_multi_cols(self, ux_bubble_csv: Path) -> None:
        """Multiple --cols work together."""
        result = invoke(
            "bubble",
            "-f",
            str(ux_bubble_csv),
            "--cols",
            "feat_a",
            "--cols",
            "feat_b",
            "--cols",
            "feat_c",
            "--y",
            "name",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "feat_a" in result.stdout
        assert "feat_b" in result.stdout
        assert "feat_c" in result.stdout

    def test_title(self, ux_bubble_csv: Path) -> None:
        """--title appears in output."""
        result = invoke(
            "bubble",
            "-f",
            str(ux_bubble_csv),
            "--cols",
            "feat_a",
            "--y",
            "name",
            "--title",
            "Features",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "Features" in result.stdout


# ============================================================================
# Summarise option tests
# ============================================================================


class TestSummariseOptions:
    def test_top_values_notation_explained(self, ux_summarise_csv: Path) -> None:
        """Top-value frequency notation should be self-explanatory (feedback #5)."""
        result = invoke(
            "summarise",
            "-f",
            str(ux_summarise_csv),
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        out = result.stdout.lower()
        # The output should either explain the (N) notation or use a clear header.
        assert "freq" in out or "count" in out or "top" in out, (
            f"No legend or explanation for top-value notation:\n{result.stdout}"
        )

    def test_sample(self, ux_summarise_csv: Path) -> None:
        """--sample 3 produces a Sample section with rows."""
        result = invoke(
            "summarise",
            "-f",
            str(ux_summarise_csv),
            "--sample",
            "3",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        out = result.stdout.lower()
        assert "sample" in out


# ============================================================================
# Cross-command tests
# ============================================================================


class TestSharedOptions:
    @pytest.mark.parametrize(
        "command,args",
        [
            ("timeline", ["--x", "start", "--x", "end", "--y", "name"]),
            ("bar", ["-c", "status"]),
            ("line", ["--x", "date", "--y", "temp"]),
            ("bubble", ["--cols", "feat_a", "--y", "name"]),
            ("summarise", []),
        ],
    )
    def test_head_limits(self, command: str, args: list[str], ux_csvs: dict[str, Path]) -> None:
        """--head 3 limits input rows for all commands."""
        csv_path = str(ux_csvs[command])
        result = invoke(command, "-f", csv_path, *args, "--head", "3", "--format", "compact")
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.stdout}"

    @pytest.mark.parametrize(
        "command,args,filter_col,filter_val",
        [
            ("timeline", ["--x", "start", "--x", "end", "--y", "name"], "category", "backend"),
            ("bar", ["-c", "status"], "assignee", "alice"),
            ("line", ["--x", "date", "--y", "temp"], "region", "north"),
            ("bubble", ["--cols", "feat_a", "--y", "name"], "category", "frontend"),
            ("summarise", [], "name", "alice"),
        ],
    )
    def test_where_filters(
        self,
        command: str,
        args: list[str],
        filter_col: str,
        filter_val: str,
        ux_csvs: dict[str, Path],
    ) -> None:
        """--where filters rows for all commands."""
        csv_path = str(ux_csvs[command])
        result = invoke(
            command,
            "-f",
            csv_path,
            *args,
            "--where",
            f"{filter_col}={filter_val}",
            "--format",
            "compact",
        )
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.stdout}"

    @pytest.mark.parametrize(
        "command,args,filter_col,filter_val",
        [
            ("timeline", ["--x", "start", "--x", "end", "--y", "name"], "category", "backend"),
            ("bar", ["-c", "status"], "assignee", "alice"),
            ("line", ["--x", "date", "--y", "temp"], "region", "north"),
            ("bubble", ["--cols", "feat_a", "--y", "name"], "category", "frontend"),
            ("summarise", [], "name", "alice"),
        ],
    )
    def test_where_not_filters(
        self,
        command: str,
        args: list[str],
        filter_col: str,
        filter_val: str,
        ux_csvs: dict[str, Path],
    ) -> None:
        """--where-not excludes matching rows for all commands."""
        csv_path = str(ux_csvs[command])
        result = invoke(
            command,
            "-f",
            csv_path,
            *args,
            "--where-not",
            f"{filter_col}={filter_val}",
            "--format",
            "compact",
        )
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.stdout}"
