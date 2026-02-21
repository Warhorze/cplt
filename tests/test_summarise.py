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

DATA_QUALITY_CSV = """\
name,amount,start_date,status,code
alice,100.5,2024-01-15,active,A1
 bob ,0,15/01/2024,N/A,B2
charlie,NA,2024-03-10,inactive,0
dave,50.0,10-03-2024,,D4
eve,0.0,2024-04-20T10:30:00,null,E5
frank,unknown,2024-06-01,active,None
grace,75,2024-07-15,active,G7
"""

HIGH_CARD_CSV_HEADER = "id,value\n"


@pytest.fixture
def data_quality_csv(tmp_path: Path) -> Path:
    p = tmp_path / "dataquality.csv"
    p.write_text(DATA_QUALITY_CSV)
    return p


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


class TestDataQualityFields:
    """Tests for new data-quality diagnostic fields on ColumnSummary."""

    def test_null_count(self, data_quality_csv: Path) -> None:
        """null_count = row_count - non_null_count, made explicit."""
        result = summarise_csv(data_quality_csv)
        status = next(s for s in result if s.name == "status")
        # dave has empty status → 1 null
        assert status.null_count == 1

    def test_null_sentinel_count(self, data_quality_csv: Path) -> None:
        """Count values matching common null sentinel strings."""
        result = summarise_csv(data_quality_csv)
        # "amount" column: "NA" (charlie) → 1 sentinel
        amount = next(s for s in result if s.name == "amount")
        assert amount.null_sentinel_count == 1
        # "status" column: "N/A" (bob), "null" (eve) → 2 sentinels
        status = next(s for s in result if s.name == "status")
        assert status.null_sentinel_count == 2
        # "code" column: "None" (frank), "0" is NOT a sentinel → 1 sentinel
        code = next(s for s in result if s.name == "code")
        assert code.null_sentinel_count == 1

    def test_zero_count_numeric(self, data_quality_csv: Path) -> None:
        """Count values that parse to 0.0 in numeric columns."""
        result = summarise_csv(data_quality_csv)
        amount = next(s for s in result if s.name == "amount")
        # bob=0, eve=0.0 → 2 zeros
        assert amount.zero_count == 2

    def test_zero_count_non_numeric(self, data_quality_csv: Path) -> None:
        """Non-numeric columns should have zero_count=0."""
        result = summarise_csv(data_quality_csv)
        name = next(s for s in result if s.name == "name")
        assert name.zero_count == 0

    def test_mean(self, data_quality_csv: Path) -> None:
        """Mean for numeric columns."""
        result = summarise_csv(data_quality_csv)
        amount = next(s for s in result if s.name == "amount")
        # numeric values: 100.5, 0, 50.0, 0.0, 75 → mean = 225.5/5 = 45.1
        assert amount.mean is not None
        assert abs(amount.mean - 45.1) < 0.01

    def test_mean_non_numeric(self, data_quality_csv: Path) -> None:
        """Non-numeric columns should have mean=None."""
        result = summarise_csv(data_quality_csv)
        name = next(s for s in result if s.name == "name")
        assert name.mean is None

    def test_stddev(self, data_quality_csv: Path) -> None:
        """Population stddev for numeric columns."""
        result = summarise_csv(data_quality_csv)
        amount = next(s for s in result if s.name == "amount")
        assert amount.stddev is not None
        # values: 100.5, 0, 50.0, 0.0, 75 → check it's roughly correct
        assert amount.stddev > 0

    def test_stddev_non_numeric(self, data_quality_csv: Path) -> None:
        result = summarise_csv(data_quality_csv)
        name = next(s for s in result if s.name == "name")
        assert name.stddev is None

    def test_date_formats(self, data_quality_csv: Path) -> None:
        """Date columns report observed format patterns with counts."""
        result = summarise_csv(data_quality_csv)
        start_date = next(s for s in result if s.name == "start_date")
        assert len(start_date.date_formats) > 0
        # Should detect multiple formats
        fmt_dict = dict(start_date.date_formats)
        # YYYY-MM-DD should be present (alice, charlie, frank, grace = 4)
        assert "YYYY-MM-DD" in fmt_dict
        assert fmt_dict["YYYY-MM-DD"] >= 3

    def test_date_formats_non_date(self, data_quality_csv: Path) -> None:
        """Non-date columns should have empty date_formats."""
        result = summarise_csv(data_quality_csv)
        name = next(s for s in result if s.name == "name")
        assert name.date_formats == []

    def test_whitespace_count(self, data_quality_csv: Path) -> None:
        """Count values with leading/trailing whitespace (non-empty after strip)."""
        result = summarise_csv(data_quality_csv)
        name = next(s for s in result if s.name == "name")
        # " bob " has leading/trailing whitespace → 1
        assert name.whitespace_count == 1

    def test_mixed_type_pct(self, data_quality_csv: Path) -> None:
        """Columns with mixed types should report percentage breakdown."""
        result = summarise_csv(data_quality_csv)
        amount = next(s for s in result if s.name == "amount")
        # amount has: 100.5, 0, NA, 50.0, 0.0, unknown, 75
        # 5 numeric, 2 text (NA, unknown) → should show mixed type info
        assert amount.mixed_type_pct != ""
        assert "numeric" in amount.mixed_type_pct.lower()
        assert "text" in amount.mixed_type_pct.lower()

    def test_mixed_type_pct_pure_column(self, data_quality_csv: Path) -> None:
        """Pure-type columns should have empty mixed_type_pct."""
        result = summarise_csv(data_quality_csv)
        name = next(s for s in result if s.name == "name")
        assert name.mixed_type_pct == ""

    def test_mixed_type_examples(self, data_quality_csv: Path) -> None:
        """Mixed columns should show example values from minority type(s)."""
        result = summarise_csv(data_quality_csv)
        amount = next(s for s in result if s.name == "amount")
        # Minority type values: "NA", "unknown"
        assert len(amount.mixed_type_examples) > 0
        assert len(amount.mixed_type_examples) <= 3

    def test_mixed_type_examples_pure_column(self, data_quality_csv: Path) -> None:
        result = summarise_csv(data_quality_csv)
        name = next(s for s in result if s.name == "name")
        assert name.mixed_type_examples == []

    def test_exclusive_type_classification(self, tmp_path: Path) -> None:
        """Each value should be classified into exactly one type for mixed_type_pct.

        A value that parses as numeric should NOT also count as text.
        """
        csv_data = "val\n1\n2\ntrue\nfalse\nhello\n"
        p = tmp_path / "exclusive.csv"
        p.write_text(csv_data)
        result = summarise_csv(p)
        col = result[0]
        # "1" and "2" are numeric; "true", "false", "hello" are text
        # Dominant type is text (3/5 = 60%), but since <95%, mixed_type_pct shown
        assert col.mixed_type_pct != ""
