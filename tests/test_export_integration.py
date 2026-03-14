"""CLI integration tests for the --export flag."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from cplt.cli import app

runner = CliRunner()


class TestExportCreatesPng:
    def test_bar_export_creates_png(self, bar_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "bar.png"
        result = runner.invoke(
            app,
            ["bar", "-f", str(bar_csv), "-c", "status", "--export", str(out)],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists()

    def test_line_export_creates_png(self, line_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "line.png"
        result = runner.invoke(
            app,
            [
                "line",
                "-f",
                str(line_csv),
                "--x",
                "date",
                "--y",
                "temperature",
                "--export",
                str(out),
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists()

    def test_timeline_export_creates_png(self, sample_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "timeline.png"
        result = runner.invoke(
            app,
            [
                "timeline",
                "-f",
                str(sample_csv),
                "--x",
                "start",
                "--x",
                "end",
                "--y",
                "name",
                "--export",
                str(out),
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists()

    def test_summarise_export_creates_png(self, bar_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "summarise.png"
        result = runner.invoke(
            app,
            ["summarise", "-f", str(bar_csv), "--export", str(out)],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists()

    def test_bubble_export_creates_png(self, bar_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "bubble.png"
        result = runner.invoke(
            app,
            [
                "bubble",
                "-f",
                str(bar_csv),
                "--cols",
                "status",
                "--cols",
                "priority",
                "--y",
                "assignee",
                "--export",
                str(out),
            ],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists()


class TestExportProducesValidImages:
    def test_bar_export_has_reasonable_dimensions(self, bar_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "bar.png"
        runner.invoke(
            app,
            ["bar", "-f", str(bar_csv), "-c", "status", "--export", str(out)],
        )
        img = Image.open(out)
        assert img.width >= 200
        assert img.height >= 100

    def test_summarise_export_has_reasonable_dimensions(
        self, bar_csv: Path, tmp_path: Path
    ) -> None:
        """Rich table exports should be wide enough for columns to be readable."""
        out = tmp_path / "summarise.png"
        runner.invoke(
            app,
            ["summarise", "-f", str(bar_csv), "--export", str(out)],
        )
        img = Image.open(out)
        assert img.width >= 400
        assert img.height >= 100

    def test_bubble_export_has_reasonable_dimensions(self, bar_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "bubble.png"
        runner.invoke(
            app,
            [
                "bubble",
                "-f",
                str(bar_csv),
                "--cols",
                "status",
                "--cols",
                "priority",
                "--y",
                "assignee",
                "--export",
                str(out),
            ],
        )
        img = Image.open(out)
        assert img.width >= 200
        assert img.height >= 100

    def test_export_still_shows_terminal_output(self, bar_csv: Path, tmp_path: Path) -> None:
        """--export should still display chart in terminal."""
        out = tmp_path / "bar.png"
        result = runner.invoke(
            app,
            ["bar", "-f", str(bar_csv), "-c", "status", "--export", str(out)],
        )
        # Terminal output should still contain chart content
        assert result.exit_code == 0
        assert len(result.stdout) > 0


class TestExportRejectsNonVisual:
    def test_bar_export_rejects_compact(self, bar_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "bar.png"
        result = runner.invoke(
            app,
            [
                "bar",
                "-f",
                str(bar_csv),
                "-c",
                "status",
                "--format",
                "compact",
                "--export",
                str(out),
            ],
        )
        assert result.exit_code == 1
        assert "--export" in result.stdout

    def test_bar_export_rejects_semantic(self, bar_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "bar.png"
        result = runner.invoke(
            app,
            [
                "bar",
                "-f",
                str(bar_csv),
                "-c",
                "status",
                "--format",
                "semantic",
                "--export",
                str(out),
            ],
        )
        assert result.exit_code == 1
        assert "--export" in result.stdout

    def test_summarise_export_rejects_compact(self, bar_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "summarise.png"
        result = runner.invoke(
            app,
            ["summarise", "-f", str(bar_csv), "--format", "compact", "--export", str(out)],
        )
        assert result.exit_code == 1
        assert "--export" in result.stdout
