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


def test_bubble_supports_sample_option(tmp_path: Path) -> None:
    csv_file = tmp_path / "sample_rows.csv"
    csv_file.write_text("name,flag\nn1,yes\nn2,\nn3,yes\nn4,\nn5,yes\n")

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
            "--sample",
            "3",
            "--format",
            "semantic",
        ],
    )

    assert result.exit_code == 0
    present = sum(name in result.stdout for name in ("n1", "n2", "n3", "n4", "n5"))
    assert present == 3


def test_bubble_transpose_compact(tmp_path: Path) -> None:
    """--transpose swaps rows and columns in compact output."""
    csv_file = tmp_path / "t.csv"
    csv_file.write_text("name,a,b\nX,1,\nY,1,1\n")

    result = runner.invoke(
        app,
        [
            "bubble",
            "-f",
            str(csv_file),
            "--cols",
            "a",
            "--cols",
            "b",
            "--y",
            "name",
            "--transpose",
            "--format",
            "compact",
        ],
    )

    assert result.exit_code == 0
    # Transposed: cols are now "X | Y", rows are "a" and "b"
    assert "cols: X | Y" in result.stdout
    # "a" row: X=T, Y=T → ●●
    assert "|●●|" in result.stdout
    # "b" row: X=F, Y=T → ·●
    assert "|·●|" in result.stdout


def test_bubble_group_by_compact(tmp_path: Path) -> None:
    """--group-by produces grouped compact output with percentages and counts."""
    csv_file = tmp_path / "group.csv"
    csv_file.write_text("name,feature,category\na,1,x\nb,,x\nc,1,y\n")

    result = runner.invoke(
        app,
        [
            "bubble",
            "-f",
            str(csv_file),
            "--cols",
            "feature",
            "--y",
            "name",
            "--group-by",
            "category",
            "--format",
            "compact",
        ],
    )

    assert result.exit_code == 0
    assert "x:50%(1/2)" in result.stdout
    assert "y:100%(1/1)" in result.stdout


def test_bubble_group_by_semantic(tmp_path: Path) -> None:
    """--group-by produces semantic output with block characters."""
    csv_file = tmp_path / "group.csv"
    csv_file.write_text("name,feature,category\na,1,x\nb,,x\nc,1,y\n")

    result = runner.invoke(
        app,
        [
            "bubble",
            "-f",
            str(csv_file),
            "--cols",
            "feature",
            "--y",
            "name",
            "--group-by",
            "category",
            "--format",
            "semantic",
        ],
    )

    assert result.exit_code == 0
    assert "x" in result.stdout
    assert "y" in result.stdout
    assert "50%" in result.stdout
    assert "100%" in result.stdout


def test_bubble_fill_rate_footer_in_semantic(tmp_path: Path) -> None:
    """Semantic bubble output includes a fill-rate TOTAL row."""
    csv_file = tmp_path / "fill.csv"
    csv_file.write_text("name,a,b\nA,1,\nB,1,1\n")

    result = runner.invoke(
        app,
        [
            "bubble",
            "-f",
            str(csv_file),
            "--cols",
            "a",
            "--cols",
            "b",
            "--y",
            "name",
            "--format",
            "semantic",
        ],
    )

    assert result.exit_code == 0
    assert "TOTAL" in result.stdout
    assert "100%" in result.stdout
    assert "50%" in result.stdout


def test_bubble_sort_by_fill(tmp_path: Path) -> None:
    """--sort fill puts most-complete rows first in compact output."""
    csv_file = tmp_path / "sort.csv"
    csv_file.write_text("name,a,b,c\nfull,1,1,1\nempty,,,\nhalf,1,,\n")

    result = runner.invoke(
        app,
        [
            "bubble",
            "-f",
            str(csv_file),
            "--cols",
            "a",
            "--cols",
            "b",
            "--cols",
            "c",
            "--y",
            "name",
            "--sort",
            "fill",
            "--format",
            "compact",
        ],
    )

    assert result.exit_code == 0
    lines = result.stdout.strip().split("\n")
    # Find rows: full (3/3) should be before half (1/3) which is before empty (0/3)
    row_lines = [ln for ln in lines if "|" in ln and "cols:" not in ln and "fill:" not in ln]
    labels = [ln.split("|")[0].strip() for ln in row_lines]
    assert labels == ["full", "half", "empty"]


def test_bubble_shows_all_rows_without_auto_cap(tmp_path: Path) -> None:
    """Bubble output is never auto-capped; all rows are shown by default."""
    csv_file = tmp_path / "many_rows.csv"
    rows = "\n".join(f"name{i},yes" for i in range(30))
    csv_file.write_text("name,flag\n" + rows + "\n")

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
    # All 30 rows should appear
    assert "name0" in result.stdout
    assert "name29" in result.stdout
    # No truncation message
    assert "more rows" not in result.stdout


def test_bubble_head_shows_truncation_footer(tmp_path: Path) -> None:
    """When --head truncates rows, show 'Showing X of Y rows' footer."""
    csv_file = tmp_path / "many_rows.csv"
    rows = "\n".join(f"name{i},yes" for i in range(30))
    csv_file.write_text("name,flag\n" + rows + "\n")

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
            "--head",
            "10",
            "--format",
            "compact",
        ],
    )

    assert result.exit_code == 0
    assert "Showing 10 of 30 rows" in result.stdout


def test_bar_labels_option_is_accepted(bar_csv) -> None:
    result = runner.invoke(
        app,
        [
            "bar",
            "-f",
            str(bar_csv),
            "-c",
            "status",
            "--labels",
            "--format",
            "compact",
        ],
    )

    assert result.exit_code == 0
    assert "[COMPACT:bar]" in result.stdout
