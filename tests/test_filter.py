"""Tests for cplt filter functionality."""

from __future__ import annotations

import csv
import io
from datetime import datetime

import pytest

from cplt.reader import filter_rows, load_bar_data, load_line_data, load_segments, parse_where

FILTER_CSV = """\
name,status,region,priority
alice,open,north,high
bob,closed,south,low
charlie,open,north,medium
dave,closed,north,high
eve,Open,south,low
"""


@pytest.fixture
def filter_csv(tmp_path):
    p = tmp_path / "filter.csv"
    p.write_text(FILTER_CSV)
    return p


class TestParseWhere:
    def test_basic_parse(self):
        col, val = parse_where("status=open")
        assert col == "status"
        assert val == "open"

    def test_value_with_equals(self):
        col, val = parse_where("desc=a=b")
        assert col == "desc"
        assert val == "a=b"

    def test_no_equals_raises(self):
        with pytest.raises(ValueError, match="Expected format"):
            parse_where("bad_syntax")

    def test_empty_column_raises(self):
        with pytest.raises(ValueError, match="Empty column"):
            parse_where("=value")

    def test_empty_placeholder_maps_to_empty(self):
        col, val = parse_where("status=(empty)")
        assert col == "status"
        assert val == ""


class TestFilterRows:
    def _rows(self, csv_text: str) -> list[dict[str, str]]:
        reader = csv.DictReader(io.StringIO(csv_text))
        return list(reader)

    def test_single_where(self):
        rows = self._rows(FILTER_CSV)
        result = list(filter_rows(iter(rows), wheres=[("status", "open")]))
        # case-insensitive: alice, charlie, eve
        assert len(result) == 3
        assert {r["name"] for r in result} == {"alice", "charlie", "eve"}

    def test_same_column_repeated_is_or(self):
        rows = self._rows(FILTER_CSV)
        result = list(filter_rows(iter(rows), wheres=[("status", "open"), ("status", "closed")]))
        # all 5 rows match (open OR closed)
        assert len(result) == 5

    def test_different_columns_is_and(self):
        rows = self._rows(FILTER_CSV)
        result = list(filter_rows(iter(rows), wheres=[("status", "open"), ("region", "north")]))
        # open AND north: alice, charlie
        assert len(result) == 2
        assert {r["name"] for r in result} == {"alice", "charlie"}

    def test_case_insensitive_by_default(self):
        rows = self._rows(FILTER_CSV)
        result = list(filter_rows(iter(rows), wheres=[("status", "Open")]))
        # Matches "open", "Open" — alice, charlie, eve
        assert len(result) == 3

    def test_column_names_case_insensitive_by_default(self):
        rows = self._rows(FILTER_CSV)
        result = list(filter_rows(iter(rows), wheres=[("STATUS", "open")]))
        assert len(result) == 3

    def test_case_sensitive(self):
        rows = self._rows(FILTER_CSV)
        result = list(filter_rows(iter(rows), wheres=[("status", "Open")], case_sensitive=True))
        # Only eve has exactly "Open"
        assert len(result) == 1
        assert result[0]["name"] == "eve"

    def test_where_not(self):
        rows = self._rows(FILTER_CSV)
        result = list(filter_rows(iter(rows), where_nots=[("status", "closed")]))
        # Excludes bob, dave → alice, charlie, eve
        assert len(result) == 3
        assert {r["name"] for r in result} == {"alice", "charlie", "eve"}

    def test_where_and_where_not_combined(self):
        rows = self._rows(FILTER_CSV)
        result = list(
            filter_rows(
                iter(rows),
                wheres=[("region", "north")],
                where_nots=[("status", "closed")],
            )
        )
        # north AND NOT closed: alice, charlie
        assert len(result) == 2
        assert {r["name"] for r in result} == {"alice", "charlie"}

    def test_no_filters_passes_all(self):
        rows = self._rows(FILTER_CSV)
        result = list(filter_rows(iter(rows)))
        assert len(result) == 5

    def test_unknown_column_raises(self):
        rows = self._rows(FILTER_CSV)
        with pytest.raises(KeyError, match="nonexistent"):
            list(filter_rows(iter(rows), wheres=[("nonexistent", "val")]))

    def test_empty_where_matches_empty_and_null_like_values(self):
        csv_text = "name,status\na,\nb,NULL\nc,None\nd,NA\ne,nan\nf,open\n"
        rows = self._rows(csv_text)
        result = list(filter_rows(iter(rows), wheres=[("status", "")]))
        assert {r["name"] for r in result} == {"a", "b", "c", "d", "e"}


class TestLoadSegmentsWithFilter:
    def test_where_filters_segments(self, sample_csv):
        segments = load_segments(
            sample_csv,
            x_pairs=[("start", "end")],
            y_col="category",
            wheres=[("category", "A")],
            open_end=datetime(2025, 1, 1),
        )
        assert all(s.y_label == "A" for s in segments)

    def test_where_not_filters_segments(self, sample_csv):
        segments = load_segments(
            sample_csv,
            x_pairs=[("start", "end")],
            y_col="category",
            where_nots=[("category", "A")],
        )
        assert all(s.y_label == "B" for s in segments)


class TestLoadBarDataWithFilter:
    def test_where_filters_bar(self, bar_csv):
        spec = load_bar_data(bar_csv, column="status", wheres=[("priority", "high")])
        # high priority rows: open (alice), closed (dave) → open=1, closed=1
        assert sum(spec.values) == 2.0


class TestLoadLineDataWithFilter:
    def test_where_filters_line(self, line_csv):
        spec = load_line_data(
            line_csv,
            x_col="date",
            y_cols=["temperature"],
            wheres=[("region", "north")],
        )
        assert len(spec.x_values) == 3
        # All north temperatures
        assert all(v < 15 for v in spec.y_series["temperature"])
