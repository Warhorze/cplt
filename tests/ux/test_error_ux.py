"""Error message quality tests.

Guards that error paths produce actionable, human-readable messages.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.ux.conftest import invoke


class TestExistingErrorPaths:
    """Regression guards for error paths that already work."""

    def test_odd_x_count(self, timeline_csv: Path) -> None:
        """Odd --x count mentions pairs or even."""
        result = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--x",
            "category",
            "--y",
            "name",
            "--format",
            "compact",
        )
        assert result.exit_code != 0
        out = result.stdout.lower()
        assert "pair" in out or "even" in out, f"Error doesn't mention pairs/even:\n{result.stdout}"

    def test_missing_y_timeline(self, timeline_csv: Path) -> None:
        """Missing --y on timeline shows an error."""
        result = invoke(
            "timeline",
            "-f",
            str(timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--format",
            "compact",
        )
        assert result.exit_code != 0

    def test_missing_column_bar(self, ux_bar_csv: Path) -> None:
        """Missing -c on bar shows an error."""
        result = invoke(
            "bar",
            "-f",
            str(ux_bar_csv),
            "--format",
            "compact",
        )
        assert result.exit_code != 0

    def test_missing_cols_bubble(self, ux_bubble_csv: Path) -> None:
        """Missing --cols on bubble shows an error."""
        result = invoke(
            "bubble",
            "-f",
            str(ux_bubble_csv),
            "--y",
            "name",
            "--format",
            "compact",
        )
        assert result.exit_code != 0

    def test_bad_where_syntax(self, ux_bar_csv: Path) -> None:
        """Malformed --where mentions expected format."""
        result = invoke(
            "bar",
            "-f",
            str(ux_bar_csv),
            "-c",
            "status",
            "--where",
            "no_equals_sign",
            "--format",
            "compact",
        )
        assert result.exit_code != 0
        out = result.stdout.lower()
        assert "format" in out or "=" in out or "expected" in out, (
            f"Error doesn't mention expected format:\n{result.stdout}"
        )

    def test_invalid_format_all_commands(
        self,
        timeline_csv: Path,
        ux_bar_csv: Path,
        ux_line_csv: Path,
        ux_bubble_csv: Path,
        ux_summarise_csv: Path,
    ) -> None:
        """Invalid --format is rejected by all commands."""
        cases = [
            ("timeline", str(timeline_csv), ["--x", "start", "--x", "end", "--y", "name"]),
            ("bar", str(ux_bar_csv), ["-c", "status"]),
            ("line", str(ux_line_csv), ["--x", "date", "--y", "temp"]),
            ("bubble", str(ux_bubble_csv), ["--cols", "feat_a", "--y", "name"]),
            ("summarise", str(ux_summarise_csv), []),
        ]
        for cmd, csv_path, args in cases:
            result = invoke(cmd, "-f", csv_path, *args, "--format", "invalid")
            assert result.exit_code == 1, f"{cmd}: exit_code={result.exit_code}"
            assert "format" in result.stdout.lower(), f"{cmd}: no 'format' in error"


    def test_invalid_sort_value(self, ux_bubble_csv: Path) -> None:
        """Invalid --sort value produces an error."""
        result = invoke(
            "bubble",
            "-f",
            str(ux_bubble_csv),
            "--cols",
            "feat_a",
            "--y",
            "name",
            "--sort",
            "invalid",
            "--format",
            "compact",
        )
        assert result.exit_code != 0
        out = result.stdout.lower()
        assert "sort" in out or "unknown" in out, (
            f"Error doesn't mention sort:\n{result.stdout}"
        )

    def test_group_by_nonexistent_column(self, ux_bubble_csv: Path) -> None:
        """--group-by with a nonexistent column produces an error with available columns."""
        result = invoke(
            "bubble",
            "-f",
            str(ux_bubble_csv),
            "--cols",
            "feat_a",
            "--y",
            "name",
            "--group-by",
            "nonexistent",
            "--format",
            "compact",
        )
        assert result.exit_code != 0
        assert "available" in result.stdout.lower(), (
            f"Error doesn't list available columns:\n{result.stdout}"
        )


class TestFeedbackDrivenErrors:
    """Tests derived from tester feedback (feedback.md)."""

    def test_no_matching_data_warns(self, ux_bar_csv: Path) -> None:
        """--where with no matches produces a warning, not a crash (feedback validation)."""
        result = invoke(
            "bar",
            "-f",
            str(ux_bar_csv),
            "-c",
            "status",
            "--where",
            "assignee=nonexistent",
            "--format",
            "compact",
        )
        out = result.stdout.lower()
        assert "warning" in out or "no data" in out, (
            f"No warning for zero-match filter:\n{result.stdout}"
        )

    @pytest.mark.xfail(reason="Feedback #4: unparseable end dates silently dropped, no warning")
    def test_unparseable_end_date_warns(self, tmp_path: Path) -> None:
        """Rows with unparseable end dates should produce a warning (feedback #4)."""
        csv = tmp_path / "bad_end.csv"
        csv.write_text("name,start,end\nA,2024-01-01,2024-01-10\nB,2024-02-01,baddate\n")
        result = invoke(
            "timeline",
            "-f",
            str(csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--format",
            "compact",
        )
        out = result.stdout.lower()
        # Should warn about skipped/unparseable rows.
        assert "warning" in out or "skip" in out or "parse" in out


class TestErrorQualityImprovements:
    """Tests for better error messages."""

    def test_unknown_column_lists_available(self, ux_bar_csv: Path) -> None:
        """Error includes 'Available:' with valid column names."""
        result = invoke(
            "bar",
            "-f",
            str(ux_bar_csv),
            "-c",
            "nonexistent",
            "--format",
            "compact",
        )
        assert result.exit_code != 0
        assert "available" in result.stdout.lower()
        # Should list actual columns
        assert "status" in result.stdout.lower()

    def test_malformed_csv_no_traceback(self, tmp_path: Path) -> None:
        """Malformed CSV produces human-readable error, not TypeError."""
        bad_csv = tmp_path / "bad.csv"
        bad_csv.write_text("a,b\n1,2,3\n4\n")
        result = invoke(
            "bar",
            "-f",
            str(bad_csv),
            "-c",
            "a",
            "--format",
            "compact",
        )
        assert "Traceback" not in result.stdout
        assert "TypeError" not in result.stdout
