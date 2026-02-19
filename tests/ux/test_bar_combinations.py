"""Cross-stage option combination tests for the bar command.

Phase 1 tests lock in current working behavior.
Phase 2 tests lock in previously broken combinations that are now fixed.
"""

from __future__ import annotations

from pathlib import Path

from tests.ux.conftest import invoke

# ============================================================================
# Phase 1: Tests that pass against current code
# ============================================================================


class TestBarCrossStageGreen:
    """Combinations that work correctly today."""

    def test_where_plus_sort_value(self, ux_bar_csv: Path) -> None:
        """--where filters rows, then --sort value orders by count."""
        result = invoke(
            "bar", "-f", str(ux_bar_csv),
            "-c", "status",
            "--where", "assignee=alice",
            "--sort", "value",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # alice has: open=2, closed=1, in_progress=1, blocked=1
        # Sort by value → open first
        lines = result.stdout.split("\n")
        statuses = ("open", "closed", "blocked", "in_progress")
        data_lines = [ln for ln in lines if any(s in ln for s in statuses)]
        assert len(data_lines) >= 1
        assert "open" in data_lines[0]  # highest count first

    def test_where_plus_top(self, ux_bar_csv: Path) -> None:
        """--where filters, then --top selects highest count from filtered set."""
        result = invoke(
            "bar", "-f", str(ux_bar_csv),
            "-c", "status",
            "--where", "assignee=alice",
            "--top", "2",
            "--format", "compact",
        )
        assert result.exit_code == 0
        lines = result.stdout.strip().split("\n")
        statuses = ("open", "closed", "blocked", "in_progress")
        data_lines = [ln for ln in lines if any(s in ln for s in statuses)]
        assert len(data_lines) <= 2

    def test_head_plus_sort(self, ux_bar_csv: Path) -> None:
        """--head limits rows, then --sort orders the counted values."""
        result = invoke(
            "bar", "-f", str(ux_bar_csv),
            "-c", "status",
            "--head", "6",
            "--sort", "value",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # First 6 rows: open(4), closed(2) → open should be first
        lines = result.stdout.split("\n")
        data_lines = [ln for ln in lines if "open" in ln or "closed" in ln]
        assert len(data_lines) >= 1

    def test_head_plus_top(self, ux_bar_csv: Path) -> None:
        """--head limits rows, --top selects highest count."""
        result = invoke(
            "bar", "-f", str(ux_bar_csv),
            "-c", "status",
            "--head", "8",
            "--top", "2",
            "--format", "compact",
        )
        assert result.exit_code == 0
        statuses = ("open", "closed", "blocked", "in_progress")
        lines = result.stdout.strip().split("\n")
        data_lines = [ln for ln in lines if any(s in ln for s in statuses)]
        assert len(data_lines) <= 2

    def test_where_plus_where_not(self, ux_bar_csv: Path) -> None:
        """--where and --where-not can be combined."""
        result = invoke(
            "bar", "-f", str(ux_bar_csv),
            "-c", "status",
            "--where", "priority=high",
            "--where-not", "assignee=charlie",
            "--format", "compact",
        )
        assert result.exit_code == 0

    def test_option_order_sort_top(self, ux_bar_csv: Path) -> None:
        """Option order must not matter: --sort before --top vs after."""
        result_a = invoke(
            "bar", "-f", str(ux_bar_csv),
            "-c", "status",
            "--sort", "value", "--top", "2",
            "--format", "compact",
        )
        result_b = invoke(
            "bar", "-f", str(ux_bar_csv),
            "-c", "status",
            "--top", "2", "--sort", "value",
            "--format", "compact",
        )
        assert result_a.exit_code == 0
        assert result_b.exit_code == 0
        assert result_a.stdout == result_b.stdout


# ============================================================================
# Phase 2: Tests for behavior that previously failed and is now fixed
# ============================================================================


class TestBarCrossStageFixed:
    """Combinations that were previously broken."""

    def test_top_plus_sort_label(self, ux_bar_csv: Path) -> None:
        """--top N should always select by count first, then --sort label the selected set.

        Current: sorts alphabetically first, then takes top N (alpha-first).
        Expected: selects top N by count, then sorts those alphabetically.
        """
        result = invoke(
            "bar", "-f", str(ux_bar_csv),
            "-c", "status",
            "--top", "2", "--sort", "label",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # Counts: open=4, blocked=3, closed=3, in_progress=2
        # Top 2 by count: open(4) + blocked(3) or closed(3)
        # Then sort label → alphabetical
        lines = result.stdout.split("\n")
        statuses = ("open", "closed", "blocked", "in_progress")
        data_lines = [ln for ln in lines if any(s in ln for s in statuses)]
        # "open" must be in the selected set (it has the highest count)
        labels = []
        for ln in data_lines:
            for s in statuses:
                if s in ln:
                    labels.append(s)
                    break
        assert "open" in labels, f"open (count=4) not in top 2: {labels}"
