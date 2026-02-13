"""Tests for csvplot.reader."""

from __future__ import annotations

from datetime import datetime

import pytest

from csvplot.reader import detect_date_columns, load_segments, parse_datetime, read_csv_header


class TestParseDatetime:
    @pytest.mark.parametrize(
        "value, expected",
        [
            ("2024-01-15", datetime(2024, 1, 15)),
            ("2024-01-15 10:30:00", datetime(2024, 1, 15, 10, 30, 0)),
            ("2024-01-15 10:30:00.123", datetime(2024, 1, 15, 10, 30, 0, 123000)),
            ("  2024-06-01  ", datetime(2024, 6, 1)),
            # ISO 8601 T-separator
            ("2024-01-15T10:30:00", datetime(2024, 1, 15, 10, 30, 0)),
            ("2024-01-15T10:30:00.123", datetime(2024, 1, 15, 10, 30, 0, 123000)),
            # EU dash format
            ("15-01-2024", datetime(2024, 1, 15)),
            ("15-01-2024 10:30:00", datetime(2024, 1, 15, 10, 30, 0)),
            # EU slash format
            ("15/01/2024", datetime(2024, 1, 15)),
            ("15/01/2024 10:30:00", datetime(2024, 1, 15, 10, 30, 0)),
        ],
    )
    def test_valid_formats(self, value: str, expected: datetime) -> None:
        assert parse_datetime(value) == expected

    @pytest.mark.parametrize(
        "value",
        [
            "",
            "   ",
            "9999-12-31 00:00:00.000",
            "9999-12-31",
            "not-a-date",
        ],
    )
    def test_returns_none(self, value: str) -> None:
        assert parse_datetime(value) is None


class TestReadCsvHeader:
    def test_reads_header(self, sample_csv) -> None:
        headers = read_csv_header(sample_csv)
        assert headers == ["name", "start", "end", "category", "color"]


class TestDetectDateColumns:
    def test_sample_csv(self, sample_csv) -> None:
        date_cols = detect_date_columns(sample_csv)
        assert "start" in date_cols
        assert "end" in date_cols
        assert "name" not in date_cols
        assert "category" not in date_cols

    def test_real_csv(self, real_csv) -> None:
        date_cols = detect_date_columns(real_csv)
        assert "DH_PV_STARTDATUM" in date_cols
        assert "EN_START_DATETIME" in date_cols
        assert "EA_END_DATETIME" in date_cols
        assert "DH_FACING_NUMMER" not in date_cols
        assert "SH_ARTIKEL_S1" not in date_cols


class TestLoadSegments:
    def test_basic_loading(self, sample_csv) -> None:
        segments = load_segments(sample_csv, x_pairs=[("start", "end")], y_col="category")
        # task1: valid start+end → segment
        # task2: valid start+end → segment
        # task3: valid start, sentinel end → no segment (no open_end)
        # task4: valid start, empty end → no segment
        # task5: empty start → no segment
        assert len(segments) == 2
        assert all(s.layer == 0 for s in segments)

    def test_open_end_replacement(self, sample_csv) -> None:
        open_end = datetime(2025, 1, 1)
        segments = load_segments(
            sample_csv, x_pairs=[("start", "end")], y_col="category", open_end=open_end
        )
        # task3 and task4 now get the open_end replacement
        assert len(segments) == 4
        sentinel_seg = [s for s in segments if s.y_label == "A" and s.end == open_end]
        assert len(sentinel_seg) == 1  # task3

    def test_color_key(self, sample_csv) -> None:
        segments = load_segments(
            sample_csv, x_pairs=[("start", "end")], y_col="category", color_col="color"
        )
        assert segments[0].color_key == "red"
        assert segments[1].color_key == "blue"

    def test_missing_column_raises(self, sample_csv) -> None:
        with pytest.raises(KeyError):
            load_segments(sample_csv, x_pairs=[("nonexistent", "end")], y_col="category")

    def test_real_csv(self, real_csv) -> None:
        """Smoke test against the actual sample data."""
        segments = load_segments(
            real_csv,
            x_pairs=[("DH_PV_STARTDATUM", "DH_PV_EINDDATUM")],
            y_col="DH_FACING_NUMMER",
            color_col="SH_ARTIKEL_S1",
        )
        assert len(segments) > 0
        assert all(s.layer == 0 for s in segments)

    def test_secondary_layer(self, real_csv) -> None:
        segments = load_segments(
            real_csv,
            x_pairs=[
                ("DH_PV_STARTDATUM", "DH_PV_EINDDATUM"),
                ("EN_START_DATETIME", "EA_END_DATETIME"),
            ],
            y_col="DH_FACING_NUMMER",
            open_end=datetime(2026, 1, 31),
        )
        primary = [s for s in segments if s.layer == 0]
        secondary = [s for s in segments if s.layer == 1]
        assert len(primary) > 0
        assert len(secondary) > 0

    def test_start_greater_than_end_swaps(self, tmp_path) -> None:
        """When start > end, segments should be swapped with a warning."""
        csv_content = "name,start,end,category\ntask1,2024-06-15,2024-01-01,A\n"
        csv_file = tmp_path / "swap.csv"
        csv_file.write_text(csv_content)

        segments = load_segments(csv_file, x_pairs=[("start", "end")], y_col="category")
        assert len(segments) == 1
        assert segments[0].start == datetime(2024, 1, 1)
        assert segments[0].end == datetime(2024, 6, 15)

    def test_head_limits_processed_rows(self, sample_csv) -> None:
        segments = load_segments(
            sample_csv,
            x_pairs=[("start", "end")],
            y_col="category",
            open_end=datetime(2025, 1, 1),
            max_rows=2,
        )
        assert len(segments) == 2
        assert [s.y_label for s in segments] == ["A", "B"]

    def test_multiple_y_columns_are_combined(self, sample_csv) -> None:
        segments = load_segments(
            sample_csv,
            x_pairs=[("start", "end")],
            y_col=["category", "name"],
        )
        assert len(segments) == 2
        assert segments[0].y_label == "A | task1"
        assert segments[1].y_label == "B | task2"
