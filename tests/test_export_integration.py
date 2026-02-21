"""CLI integration tests for the --export flag."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from csvplot.cli import app

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
            ["line", "-f", str(line_csv), "--x", "date", "--y", "temperature",
             "--export", str(out)],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists()

    def test_timeline_export_creates_png(self, sample_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "timeline.png"
        result = runner.invoke(
            app,
            ["timeline", "-f", str(sample_csv), "--x", "start", "--x", "end",
             "--y", "name", "--export", str(out)],
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
            ["bubble", "-f", str(bar_csv), "--cols", "status", "--cols", "priority",
             "--y", "assignee", "--export", str(out)],
        )
        assert result.exit_code == 0, result.stdout
        assert out.exists()


class TestExportRejectsNonVisual:
    def test_bar_export_rejects_compact(self, bar_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "bar.png"
        result = runner.invoke(
            app,
            ["bar", "-f", str(bar_csv), "-c", "status", "--format", "compact",
             "--export", str(out)],
        )
        assert result.exit_code == 1
        assert "--export" in result.stdout

    def test_bar_export_rejects_semantic(self, bar_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "bar.png"
        result = runner.invoke(
            app,
            ["bar", "-f", str(bar_csv), "-c", "status", "--format", "semantic",
             "--export", str(out)],
        )
        assert result.exit_code == 1
        assert "--export" in result.stdout

    def test_summarise_export_rejects_compact(self, bar_csv: Path, tmp_path: Path) -> None:
        out = tmp_path / "summarise.png"
        result = runner.invoke(
            app,
            ["summarise", "-f", str(bar_csv), "--format", "compact",
             "--export", str(out)],
        )
        assert result.exit_code == 1
        assert "--export" in result.stdout
