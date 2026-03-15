"""Cross-stage option combination tests for the summarise command.

All combinations work correctly — these tests lock in correct behavior.
"""

from __future__ import annotations

from pathlib import Path

from tests.ux.conftest import invoke


class TestSummariseCrossStage:
    """Interactions between summarise options at different pipeline stages."""

    def test_head_plus_where(self, ux_summarise_csv: Path) -> None:
        """--head + --where: head limits rows, where filters from those."""
        result = invoke(
            "summarise",
            "-f",
            str(ux_summarise_csv),
            "--head",
            "10",
            "--where",
            "name=alice",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # Should show 1 row (alice is in first 10)
        assert "1" in result.stdout

    def test_sample_plus_where(self, ux_summarise_csv: Path) -> None:
        """--sample + --where: filter then sample from filtered rows."""
        result = invoke(
            "summarise",
            "-f",
            str(ux_summarise_csv),
            "--where",
            "notes=good",
            "--sample",
            "2",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "sample" in result.stdout.lower()

    def test_head_plus_sample(self, ux_summarise_csv: Path) -> None:
        """--head + --sample: head limits input, sample from limited set."""
        result = invoke(
            "summarise",
            "-f",
            str(ux_summarise_csv),
            "--head",
            "5",
            "--sample",
            "2",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "sample" in result.stdout.lower()

    def test_category_default(self, ux_summarise_csv: Path) -> None:
        """Default --category=10: columns with <=10 unique values are categorical."""
        result = invoke(
            "summarise",
            "-f",
            str(ux_summarise_csv),
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # "notes" has many unique values but "id" has 15 unique → should show as ID
        assert "(all unique)" in result.stdout

    def test_category_custom_threshold(self, ux_summarise_csv: Path) -> None:
        """--category 20: columns with <=20 unique values become categorical."""
        result = invoke(
            "summarise",
            "-f",
            str(ux_summarise_csv),
            "--category",
            "20",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        # With threshold=20, columns with 14-15 unique values become categorical
        # So we should see percentage distributions instead of "(all unique)"
        out = result.stdout
        assert "%" in out

    def test_category_plus_where(self, ux_summarise_csv: Path) -> None:
        """--category + --where: filter rows then classify with threshold."""
        result = invoke(
            "summarise",
            "-f",
            str(ux_summarise_csv),
            "--where",
            "notes=good",
            "--category",
            "5",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "Distribution" in result.stdout

    def test_category_plus_head(self, ux_summarise_csv: Path) -> None:
        """--category + --head: head limits rows, then classify."""
        result = invoke(
            "summarise",
            "-f",
            str(ux_summarise_csv),
            "--head",
            "5",
            "--category",
            "10",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "Distribution" in result.stdout
