"""Tests for csvplot summarise functionality."""

from __future__ import annotations

from pathlib import Path

import pytest

from csvplot.summarise import summarise_csv

MIXED_CSV = """\
name,score,date,notes
alice,95.5,2024-01-01,good
bob,82,2024-02-15,ok
charlie,N/A,2024-03-10,bad
dave,70,not_a_date,
eve,88.5,2024-04-20,good
"""

HIGH_CARD_CSV_HEADER = "id,value\n"


@pytest.fixture
def mixed_csv(tmp_path: Path) -> Path:
    p = tmp_path / "mixed.csv"
    p.write_text(MIXED_CSV)
    return p


@pytest.fixture
def high_card_csv(tmp_path: Path) -> Path:
    """CSV with a high-cardinality column (100 unique values)."""
    lines = [HIGH_CARD_CSV_HEADER]
    for i in range(100):
        lines.append(f"id_{i},val_{i}\n")
    p = tmp_path / "highcard.csv"
    p.write_text("".join(lines))
    return p


@pytest.fixture
def empty_csv(tmp_path: Path) -> Path:
    p = tmp_path / "empty.csv"
    p.write_text("name,score,date\n")
    return p


class TestSummariseCsv:
    def test_basic_summary(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv)
        assert len(result) == 4  # 4 columns
        names = [s.name for s in result]
        assert names == ["name", "score", "date", "notes"]

    def test_row_count(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv)
        for s in result:
            assert s.row_count == 5

    def test_type_detection_numeric(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv)
        score = next(s for s in result if s.name == "score")
        assert score.detected_type == "numeric"

    def test_type_detection_date(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv)
        date = next(s for s in result if s.name == "date")
        assert date.detected_type == "date"

    def test_type_detection_text(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv)
        name = next(s for s in result if s.name == "name")
        assert name.detected_type == "text"

    def test_non_null_count(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv)
        notes = next(s for s in result if s.name == "notes")
        # dave has empty notes
        assert notes.non_null_count == 4

    def test_unique_count(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv)
        notes = next(s for s in result if s.name == "notes")
        # good, ok, bad, "" → 3 non-null unique
        assert notes.unique_count == 3

    def test_min_max_numeric(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv)
        score = next(s for s in result if s.name == "score")
        assert score.min_val == "70.0"
        assert score.max_val == "95.5"

    def test_min_max_date(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv)
        date = next(s for s in result if s.name == "date")
        assert "2024-01-01" in date.min_val
        assert "2024-04-20" in date.max_val

    def test_top_values(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv)
        notes = next(s for s in result if s.name == "notes")
        # "good" appears 2x, others 1x
        assert notes.top_values[0] == ("good", 2)

    def test_empty_csv(self, empty_csv: Path) -> None:
        result = summarise_csv(empty_csv)
        assert len(result) == 3
        for s in result:
            assert s.row_count == 0
            assert s.non_null_count == 0

    def test_with_where_filter(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv, wheres=[("notes", "good")])
        # Only alice and eve
        for s in result:
            assert s.row_count == 2

    def test_with_head(self, mixed_csv: Path) -> None:
        result = summarise_csv(mixed_csv, max_rows=2)
        for s in result:
            assert s.row_count == 2

    def test_sample_rows(self, mixed_csv: Path) -> None:
        _, sample = summarise_csv(mixed_csv, sample_n=3, return_sample=True)
        assert len(sample) == 3

    def test_sample_larger_than_data(self, mixed_csv: Path) -> None:
        _, sample = summarise_csv(mixed_csv, sample_n=100, return_sample=True)
        assert len(sample) == 5  # all rows

    def test_high_cardinality_guard(self, tmp_path: Path) -> None:
        """Counter should cap and report high cardinality."""
        lines = ["id\n"]
        for i in range(15000):
            lines.append(f"id_{i}\n")
        p = tmp_path / "huge.csv"
        p.write_text("".join(lines))
        result = summarise_csv(p)
        col = result[0]
        assert col.high_cardinality is True
        assert col.unique_count >= 10000
