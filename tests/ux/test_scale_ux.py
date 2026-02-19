"""Scale tests: large data behavior.

Generate CSVs programmatically and assert the CLI doesn't crash or hang.
No content assertions beyond exit code — the goal is 'doesn't crash.'
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

import pytest

from tests.ux.conftest import invoke


@pytest.fixture
def scale_timeline_csv(tmp_path: Path) -> Path:
    """500 timeline rows, 1 layer."""
    p = tmp_path / "scale_timeline.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "start", "end", "category"])
        for i in range(500):
            month = (i % 12) + 1
            day = (i % 28) + 1
            w.writerow(
                [
                    f"task_{i}",
                    f"2024-{month:02d}-{day:02d}",
                    f"2024-{month:02d}-{min(day + 5, 28):02d}",
                    random.choice(["A", "B", "C"]),
                ]
            )
    return p


@pytest.fixture
def scale_bar_csv(tmp_path: Path) -> Path:
    """5000 rows, 50 distinct status values."""
    p = tmp_path / "scale_bar.csv"
    statuses = [f"status_{i}" for i in range(50)]
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["status", "assignee"])
        for i in range(5000):
            w.writerow([random.choice(statuses), f"user_{i % 20}"])
    return p


@pytest.fixture
def scale_bubble_csv(tmp_path: Path) -> Path:
    """2000 rows, 3 feature columns + category."""
    p = tmp_path / "scale_bubble.csv"
    categories = ["alpha", "beta", "gamma", "delta"]
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "feat_a", "feat_b", "feat_c", "category"])
        for i in range(2000):
            w.writerow(
                [
                    f"item_{i}",
                    random.choice(["yes", "no", ""]),
                    random.choice(["true", "false", ""]),
                    random.choice(["1", "0", ""]),
                    random.choice(categories),
                ]
            )
    return p


@pytest.fixture
def scale_summarise_csv(tmp_path: Path) -> Path:
    """10000 rows, 3 columns."""
    p = tmp_path / "scale_summarise.csv"
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "value", "category"])
        for i in range(10000):
            w.writerow([i, round(random.uniform(0, 100), 2), random.choice(["X", "Y", "Z"])])
    return p


class TestScale:
    def test_timeline_500_rows(self, scale_timeline_csv: Path) -> None:
        result = invoke(
            "timeline",
            "-f",
            str(scale_timeline_csv),
            "--x",
            "start",
            "--x",
            "end",
            "--y",
            "name",
            "--format",
            "compact",
        )
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.stdout}"

    def test_bar_5k_rows(self, scale_bar_csv: Path) -> None:
        result = invoke(
            "bar",
            "-f",
            str(scale_bar_csv),
            "-c",
            "status",
            "--format",
            "compact",
        )
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.stdout}"

    def test_bubble_2k_rows(self, scale_bubble_csv: Path) -> None:
        result = invoke(
            "bubble",
            "-f",
            str(scale_bubble_csv),
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
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.stdout}"

    def test_bubble_2k_rows_sorted(self, scale_bubble_csv: Path) -> None:
        result = invoke(
            "bubble",
            "-f",
            str(scale_bubble_csv),
            "--cols",
            "feat_a",
            "--cols",
            "feat_b",
            "--cols",
            "feat_c",
            "--y",
            "name",
            "--sort",
            "fill",
            "--format",
            "compact",
        )
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.stdout}"

    def test_bubble_2k_rows_grouped(self, scale_bubble_csv: Path) -> None:
        result = invoke(
            "bubble",
            "-f",
            str(scale_bubble_csv),
            "--cols",
            "feat_a",
            "--cols",
            "feat_b",
            "--cols",
            "feat_c",
            "--y",
            "name",
            "--group-by",
            "category",
            "--format",
            "compact",
        )
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.stdout}"
        assert "overall:" in result.stdout

    def test_bubble_2k_rows_transposed(self, scale_bubble_csv: Path) -> None:
        result = invoke(
            "bubble",
            "-f",
            str(scale_bubble_csv),
            "--cols",
            "feat_a",
            "--cols",
            "feat_b",
            "--cols",
            "feat_c",
            "--y",
            "name",
            "--transpose",
            "--format",
            "compact",
        )
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.stdout}"

    def test_summarise_10k_rows(self, scale_summarise_csv: Path) -> None:
        result = invoke(
            "summarise",
            "-f",
            str(scale_summarise_csv),
            "--format",
            "compact",
        )
        assert result.exit_code == 0, f"exit_code={result.exit_code}\n{result.stdout}"
        # Should report correct row count.
        assert "10000" in result.stdout or "10,000" in result.stdout or "10000" in result.stdout
