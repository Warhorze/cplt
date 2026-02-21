"""Tests for csvplot.reader."""

from __future__ import annotations

from datetime import datetime

import pytest

from csvplot.reader import (
    detect_date_columns,
    detect_numeric_columns,
    load_bar_data,
    load_dots,
    load_line_data,
    load_segments,
    parse_datetime,
    read_csv_header,
)


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

    def test_open_end_does_not_replace_invalid_non_empty_end(self, tmp_path) -> None:
        csv_content = "name,start,end,category\ntask1,2024-01-01,not-a-date,A\n"
        csv_file = tmp_path / "bad_end.csv"
        csv_file.write_text(csv_content)

        segments = load_segments(
            csv_file, x_pairs=[("start", "end")], y_col="category", open_end=datetime(2025, 1, 1)
        )
        assert segments == []

    def test_warns_on_unparseable_end_dates(self, tmp_path, capsys) -> None:
        csv_content = (
            "name,start,end,category\n"
            "task1,2024-01-01,not-a-date,A\n"
            "task2,2024-01-01,also-bad,B\n"
            "task3,2024-01-01,2024-06-01,C\n"
        )
        csv_file = tmp_path / "bad_ends.csv"
        csv_file.write_text(csv_content)

        segments = load_segments(csv_file, x_pairs=[("start", "end")], y_col="category")
        assert len(segments) == 1
        captured = capsys.readouterr()
        assert "skipped 2 row(s) with unparseable dates" in captured.err

    def test_warns_on_unparseable_start_dates(self, tmp_path, capsys) -> None:
        csv_content = (
            "name,start,end,category\ntask1,garbage,2024-06-01,A\ntask2,2024-01-01,2024-06-01,B\n"
        )
        csv_file = tmp_path / "bad_starts.csv"
        csv_file.write_text(csv_content)

        segments = load_segments(csv_file, x_pairs=[("start", "end")], y_col="category")
        assert len(segments) == 1
        captured = capsys.readouterr()
        assert "skipped 1 row(s) with unparseable dates" in captured.err

    def test_no_warning_when_all_dates_valid(self, sample_csv, capsys) -> None:
        load_segments(sample_csv, x_pairs=[("start", "end")], y_col="category")
        captured = capsys.readouterr()
        assert "skipped" not in captured.err

    def test_color_key(self, sample_csv) -> None:
        segments = load_segments(
            sample_csv, x_pairs=[("start", "end")], y_col="category", color_col="color"
        )
        assert segments[0].color_key == "red"
        assert segments[1].color_key == "blue"

    def test_color_key_missing_value_group(self, tmp_path) -> None:
        csv_content = (
            "name,start,end,category,color\n"
            "task1,2024-01-01,2024-01-02,A,\n"
            "task2,2024-01-03,2024-01-04,A,blue\n"
        )
        csv_file = tmp_path / "missing_color.csv"
        csv_file.write_text(csv_content)

        segments = load_segments(
            csv_file, x_pairs=[("start", "end")], y_col="category", color_col="color"
        )
        assert segments[0].color_key == "(missing)"
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

    def test_malformed_csv_raises_clear_error(self, tmp_path) -> None:
        csv_content = "name,start,end\nitem1,2024-01-01\n"
        csv_file = tmp_path / "malformed.csv"
        csv_file.write_text(csv_content)

        with pytest.raises(ValueError, match="Failed to read CSV: row 2 has missing columns"):
            load_segments(csv_file, x_pairs=[("start", "end")], y_col="name")


class TestDetectNumericColumns:
    def test_sample_csv(self, sample_csv) -> None:
        num_cols = detect_numeric_columns(sample_csv)
        # sample_csv has no numeric columns
        assert "name" not in num_cols
        assert "category" not in num_cols

    def test_numeric_csv(self, numeric_csv) -> None:
        num_cols = detect_numeric_columns(numeric_csv)
        assert "score" in num_cols
        assert "name" not in num_cols
        assert "notes" not in num_cols

    def test_line_csv(self, line_csv) -> None:
        num_cols = detect_numeric_columns(line_csv)
        assert "temperature" in num_cols
        assert "humidity" in num_cols
        assert "date" not in num_cols
        assert "region" not in num_cols


class TestLoadBarData:
    def test_basic_counting(self, bar_csv) -> None:
        spec = load_bar_data(bar_csv, column="status")
        assert set(spec.labels) == {"open", "closed"}
        # open=3, closed=2
        idx_open = spec.labels.index("open")
        idx_closed = spec.labels.index("closed")
        assert spec.values[idx_open] == 3.0
        assert spec.values[idx_closed] == 2.0

    def test_sort_by_value(self, bar_csv) -> None:
        spec = load_bar_data(bar_csv, column="status", sort_by="value")
        assert spec.labels[0] == "open"  # 3 > 2

    def test_sort_by_label(self, bar_csv) -> None:
        spec = load_bar_data(bar_csv, column="status", sort_by="label")
        assert spec.labels == ["closed", "open"]

    def test_sort_none(self, bar_csv) -> None:
        spec = load_bar_data(bar_csv, column="status", sort_by="none")
        assert spec.labels[0] == "open"  # first in CSV

    def test_invalid_sort_raises(self, bar_csv) -> None:
        with pytest.raises(ValueError, match="Invalid sort_by"):
            load_bar_data(bar_csv, column="status", sort_by="invalid")  # type: ignore[arg-type]

    def test_top_limits(self, bar_csv) -> None:
        spec = load_bar_data(bar_csv, column="assignee", sort_by="value", top=2)
        assert len(spec.labels) == 2

    def test_head_limits_rows(self, bar_csv) -> None:
        spec = load_bar_data(bar_csv, column="status", max_rows=2)
        # Only first 2 rows: open, closed
        assert sum(spec.values) == 2.0

    def test_missing_column(self, bar_csv) -> None:
        with pytest.raises(KeyError):
            load_bar_data(bar_csv, column="nonexistent")

    def test_malformed_bar_data_raises_clear_error(self, tmp_path) -> None:
        csv_content = "status,assignee\nopen\n"
        csv_file = tmp_path / "malformed_bar.csv"
        csv_file.write_text(csv_content)

        with pytest.raises(ValueError, match="Failed to read CSV: row 2 has missing columns"):
            load_bar_data(csv_file, column="status")

    def test_horizontal(self, bar_csv) -> None:
        spec = load_bar_data(bar_csv, column="status", horizontal=True)
        assert spec.horizontal is True


class TestLoadLineData:
    def test_basic_loading(self, line_csv) -> None:
        spec = load_line_data(line_csv, x_col="date", y_cols=["temperature"])
        assert len(spec.x_values) == 6
        assert "temperature" in spec.y_series
        assert len(spec.y_series["temperature"]) == 6
        assert spec.x_is_date is True

    def test_multiple_y_columns(self, line_csv) -> None:
        spec = load_line_data(line_csv, x_col="date", y_cols=["temperature", "humidity"])
        assert "temperature" in spec.y_series
        assert "humidity" in spec.y_series

    def test_color_grouping(self, line_csv) -> None:
        spec = load_line_data(line_csv, x_col="date", y_cols=["temperature"], color_col="region")
        assert "north" in spec.y_series
        assert "south" in spec.y_series
        assert len(spec.x_values) == 3  # 3 unique dates

    def test_non_numeric_handling(self, numeric_csv) -> None:
        spec = load_line_data(numeric_csv, x_col="name", y_cols=["score"])
        assert spec.x_is_date is False
        assert len(spec.y_series["score"]) == 4
        # "not_a_number" and "" should become NaN
        import math

        assert math.isnan(spec.y_series["score"][2])
        assert math.isnan(spec.y_series["score"][3])

    def test_date_detection(self, line_csv) -> None:
        spec = load_line_data(line_csv, x_col="date", y_cols=["temperature"])
        assert spec.x_is_date is True

    def test_head_limits_rows(self, line_csv) -> None:
        spec = load_line_data(line_csv, x_col="date", y_cols=["temperature"], max_rows=3)
        assert len(spec.x_values) == 3

    def test_missing_column(self, line_csv) -> None:
        with pytest.raises(KeyError):
            load_line_data(line_csv, x_col="nonexistent", y_cols=["temperature"])

    def test_malformed_line_data_raises_clear_error(self, tmp_path) -> None:
        csv_content = "date,temperature\n2024-01-01\n"
        csv_file = tmp_path / "malformed_line.csv"
        csv_file.write_text(csv_content)

        with pytest.raises(ValueError, match="Failed to read CSV: row 2 has missing columns"):
            load_line_data(csv_file, x_col="date", y_cols=["temperature"])

    def test_date_x_drops_invalid_rows(self, tmp_path) -> None:
        csv_content = "date,temperature\n2024-01-01,10\n,11\n2024-01-03,12\n"
        csv_file = tmp_path / "bad_line.csv"
        csv_file.write_text(csv_content)

        spec = load_line_data(csv_file, x_col="date", y_cols=["temperature"])
        assert spec.x_is_date is True
        assert spec.x_values == ["2024-01-01", "2024-01-03"]
        assert spec.y_series["temperature"] == [10.0, 12.0]


class TestLoadDots:
    def test_basic_loading(self, tmp_path) -> None:
        csv_content = (
            "name,start,end,due_date\n"
            "Alpha,2024-01-01,2024-01-15,2024-01-10\n"
            "Bravo,2024-02-01,2024-02-20,2024-02-15\n"
        )
        csv_file = tmp_path / "dots.csv"
        csv_file.write_text(csv_content)

        dots = load_dots(csv_file, dot_cols=["due_date"], y_col=["name"])
        assert len(dots) == 2
        assert dots[0].y_label == "Alpha"
        assert dots[0].date == datetime(2024, 1, 10)
        assert dots[0].layer == 0
        assert dots[1].y_label == "Bravo"

    def test_skip_empty_dates(self, tmp_path) -> None:
        csv_content = (
            "name,start,end,due_date\n"
            "Alpha,2024-01-01,2024-01-15,2024-01-10\n"
            "Bravo,2024-02-01,2024-02-20,\n"
            "Charlie,2024-03-01,2024-03-15,2024-03-10\n"
        )
        csv_file = tmp_path / "dots.csv"
        csv_file.write_text(csv_content)

        dots = load_dots(csv_file, dot_cols=["due_date"], y_col=["name"])
        assert len(dots) == 2
        assert dots[0].y_label == "Alpha"
        assert dots[1].y_label == "Charlie"

    def test_multiple_dot_cols(self, tmp_path) -> None:
        csv_content = "name,due_date,review_date\nAlpha,2024-01-10,2024-01-12\nBravo,2024-02-15,\n"
        csv_file = tmp_path / "dots.csv"
        csv_file.write_text(csv_content)

        dots = load_dots(csv_file, dot_cols=["due_date", "review_date"], y_col=["name"])
        assert len(dots) == 3
        # Alpha has both due_date (layer 0) and review_date (layer 1)
        alpha_dots = [d for d in dots if d.y_label == "Alpha"]
        assert len(alpha_dots) == 2
        assert alpha_dots[0].layer == 0
        assert alpha_dots[1].layer == 1
        # Bravo has only due_date (layer 0), review_date is empty
        bravo_dots = [d for d in dots if d.y_label == "Bravo"]
        assert len(bravo_dots) == 1
        assert bravo_dots[0].layer == 0

    def test_with_color_col(self, tmp_path) -> None:
        csv_content = (
            "name,due_date,category\nAlpha,2024-01-10,backend\nBravo,2024-02-15,frontend\n"
        )
        csv_file = tmp_path / "dots.csv"
        csv_file.write_text(csv_content)

        dots = load_dots(csv_file, dot_cols=["due_date"], y_col=["name"], color_col="category")
        assert len(dots) == 2
        assert dots[0].color_key == "backend"
        assert dots[1].color_key == "frontend"

    def test_with_filter(self, tmp_path) -> None:
        csv_content = (
            "name,due_date,category\n"
            "Alpha,2024-01-10,backend\n"
            "Bravo,2024-02-15,frontend\n"
            "Charlie,2024-03-10,backend\n"
        )
        csv_file = tmp_path / "dots.csv"
        csv_file.write_text(csv_content)

        dots = load_dots(
            csv_file,
            dot_cols=["due_date"],
            y_col=["name"],
            wheres=[("category", "backend")],
        )
        assert len(dots) == 2
        assert dots[0].y_label == "Alpha"
        assert dots[1].y_label == "Charlie"

    def test_composite_y_label(self, tmp_path) -> None:
        csv_content = "name,category,due_date\nAlpha,backend,2024-01-10\n"
        csv_file = tmp_path / "dots.csv"
        csv_file.write_text(csv_content)

        dots = load_dots(csv_file, dot_cols=["due_date"], y_col=["name", "category"])
        assert len(dots) == 1
        assert dots[0].y_label == "Alpha | backend"
