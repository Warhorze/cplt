"""UX tests for hist command option combinations."""

from __future__ import annotations

from pathlib import Path

from tests.ux.conftest import invoke


class TestHistCombinations:
    def test_basic(self, ux_hist_csv: Path) -> None:
        result = invoke("hist", "-f", str(ux_hist_csv), "-c", "score", "--format", "compact")
        assert result.exit_code == 0
        assert "[COMPACT:hist]" in result.stdout

    def test_with_bins(self, ux_hist_csv: Path) -> None:
        result = invoke(
            "hist", "-f", str(ux_hist_csv), "-c", "score", "--bins", "3", "--format", "compact"
        )
        assert result.exit_code == 0
        assert "bins=3" in result.stdout

    def test_with_where(self, ux_hist_csv: Path) -> None:
        result = invoke(
            "hist",
            "-f",
            str(ux_hist_csv),
            "-c",
            "score",
            "--where",
            "grade=A",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "n=6" in result.stdout

    def test_with_head(self, ux_hist_csv: Path) -> None:
        result = invoke(
            "hist", "-f", str(ux_hist_csv), "-c", "score", "--head", "5", "--format", "compact"
        )
        assert result.exit_code == 0
        assert "n=4" in result.stdout

    def test_with_title(self, ux_hist_csv: Path) -> None:
        result = invoke(
            "hist",
            "-f",
            str(ux_hist_csv),
            "-c",
            "score",
            "--title",
            "My Histogram",
            "--format",
            "compact",
        )
        assert result.exit_code == 0
        assert "My Histogram" in result.stdout
