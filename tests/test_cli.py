"""CLI-level tests for shared option behavior."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from csvplot.cli import app

runner = CliRunner()


def test_bar_rejects_invalid_format(bar_csv) -> None:
    result = runner.invoke(
        app,
        ["bar", "-f", str(bar_csv), "-c", "status", "--format", "invalid"],
    )
    assert result.exit_code == 1
    assert "--format must be 'visual', 'compact', or 'semantic'" in result.stdout


def test_line_rejects_invalid_format(line_csv) -> None:
    result = runner.invoke(
        app,
        ["line", "-f", str(line_csv), "--x", "date", "--y", "temperature", "--format", "invalid"],
    )
    assert result.exit_code == 1
    assert "--format must be 'visual', 'compact', or 'semantic'" in result.stdout


def test_summarise_rejects_invalid_format(sample_csv) -> None:
    result = runner.invoke(
        app,
        ["summarise", "-f", str(sample_csv), "--format", "invalid"],
    )
    assert result.exit_code == 1
    assert "--format must be 'visual', 'compact', or 'semantic'" in result.stdout


def test_bubble_rejects_invalid_format(sample_csv) -> None:
    result = runner.invoke(
        app,
        ["bubble", "-f", str(sample_csv), "--cols", "name", "--y", "name", "--format", "invalid"],
    )
    assert result.exit_code == 1
    assert "--format must be 'visual', 'compact', or 'semantic'" in result.stdout


def test_bubble_color_changes_visual_output() -> None:
    result_plain = runner.invoke(
        app,
        [
            "bubble",
            "-f",
            "data/titanic.csv",
            "--cols",
            "Cabin",
            "--cols",
            "Age",
            "--cols",
            "Embarked",
            "--y",
            "Name",
            "--head",
            "12",
        ],
    )
    result_color = runner.invoke(
        app,
        [
            "bubble",
            "-f",
            "data/titanic.csv",
            "--cols",
            "Cabin",
            "--cols",
            "Age",
            "--cols",
            "Embarked",
            "--y",
            "Name",
            "--color",
            "Pclass",
            "--head",
            "12",
        ],
    )

    assert result_plain.exit_code == 0
    assert result_color.exit_code == 0
    assert result_plain.stdout != result_color.stdout
    assert "Legend" in result_color.stdout


def test_bubble_does_not_number_rows_without_truncation(tmp_path: Path) -> None:
    csv_file = tmp_path / "short_labels.csv"
    csv_file.write_text("name,flag\nalice,yes\nbob,\n")

    result = runner.invoke(
        app,
        [
            "bubble",
            "-f",
            str(csv_file),
            "--cols",
            "flag",
            "--y",
            "name",
            "--format",
            "semantic",
        ],
    )

    assert result.exit_code == 0
    assert "alice" in result.stdout
    assert "1. alice" not in result.stdout


def test_bubble_numbers_rows_when_labels_are_truncated(tmp_path: Path) -> None:
    csv_file = tmp_path / "long_labels.csv"
    long_name = "a" * 60
    csv_file.write_text(f"name,flag\n{long_name},yes\nbob,\n")

    result = runner.invoke(
        app,
        [
            "bubble",
            "-f",
            str(csv_file),
            "--cols",
            "flag",
            "--y",
            "name",
            "--format",
            "semantic",
        ],
    )

    assert result.exit_code == 0
    assert "1. " in result.stdout
    assert "Row Labels" in result.stdout
