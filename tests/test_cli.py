"""CLI-level tests for shared option behavior."""

from __future__ import annotations

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
