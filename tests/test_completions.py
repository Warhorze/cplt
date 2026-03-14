"""Tests for cplt.completions."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cplt.completions import (
    _matches_keywords,
    _sort_columns_for_position,
    complete_column,
    complete_date_column,
)


class TestMatchesKeywords:
    def test_start_keyword(self) -> None:
        assert _matches_keywords("DH_PV_STARTDATUM", {"start", "begin"})

    def test_end_keyword(self) -> None:
        assert _matches_keywords("EA_END_DATETIME", {"end", "eind"})

    def test_dutch_keyword(self) -> None:
        assert _matches_keywords("DH_PV_EINDDATUM", {"eind"})

    def test_no_match(self) -> None:
        assert not _matches_keywords("DH_FACING_NUMMER", {"start", "end"})

    def test_case_insensitive(self) -> None:
        assert _matches_keywords("START_DATE", {"start"})
        assert _matches_keywords("start_date", {"start"})


class TestSortColumnsForPosition:
    @pytest.fixture
    def date_columns(self) -> list[str]:
        return [
            "DH_PV_EINDDATUM",
            "DH_PV_STARTDATUM",
            "EA_END_DATETIME",
            "EN_START_DATETIME",
            "TA_INSERT_DATETIME",
            "TA_UPDATE_DATETIME",
        ]

    def test_even_position_sorts_start_first(self, date_columns: list[str]) -> None:
        result = _sort_columns_for_position(date_columns, position=0)
        # Start-like columns should come first
        assert result[0] == "DH_PV_STARTDATUM"
        assert result[1] == "EN_START_DATETIME"

    def test_odd_position_sorts_end_first(self, date_columns: list[str]) -> None:
        result = _sort_columns_for_position(date_columns, position=1)
        # End-like columns should come first
        assert result[0] == "DH_PV_EINDDATUM"
        assert result[1] == "EA_END_DATETIME"

    def test_position_2_is_start(self, date_columns: list[str]) -> None:
        result = _sort_columns_for_position(date_columns, position=2)
        assert result[0] == "DH_PV_STARTDATUM"

    def test_position_3_is_end(self, date_columns: list[str]) -> None:
        result = _sort_columns_for_position(date_columns, position=3)
        assert result[0] == "DH_PV_EINDDATUM"

    def test_non_matching_columns_sorted_alphabetically(self, date_columns: list[str]) -> None:
        result = _sort_columns_for_position(date_columns, position=0)
        non_start = [c for c in result if "START" not in c.upper()]
        assert non_start == sorted(non_start)


class TestCompleteColumn:
    def test_returns_matching_columns(self, sample_csv) -> None:
        ctx = MagicMock()
        ctx.params = {"file": sample_csv}
        result = complete_column(ctx, [], "ca")
        assert "category" in result

    def test_returns_all_on_empty(self, sample_csv) -> None:
        ctx = MagicMock()
        ctx.params = {"file": sample_csv}
        result = complete_column(ctx, [], "")
        assert set(result) == {"name", "start", "end", "category", "color"}

    def test_no_file_returns_empty(self) -> None:
        ctx = MagicMock()
        ctx.params = {"file": None}
        result = complete_column(ctx, [], "")
        assert result == []

    def test_tilde_path_is_resolved(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        home = tmp_path / "home"
        csv_dir = home / "data"
        csv_dir.mkdir(parents=True)
        csv_path = csv_dir / "sample.csv"
        csv_path.write_text("name,age\nalice,30\n")
        monkeypatch.setenv("HOME", str(home))

        ctx = MagicMock()
        ctx.params = {"file": "~/data/sample.csv"}
        result = complete_column(ctx, [], "")
        assert "name" in result
        assert "age" in result


class TestCompleteDateColumn:
    def test_returns_only_date_columns(self, sample_csv) -> None:
        ctx = MagicMock()
        ctx.params = {"file": sample_csv, "x": []}
        result = complete_date_column(ctx, [], "")
        assert "start" in result
        assert "end" in result
        assert "name" not in result
        assert "category" not in result

    def test_smart_ordering_start_position(self, sample_csv) -> None:
        ctx = MagicMock()
        ctx.params = {"file": sample_csv, "x": []}  # position 0 = start
        result = complete_date_column(ctx, [], "")
        # "start" contains start keyword, should come before "end"
        assert result.index("start") < result.index("end")

    def test_smart_ordering_end_position(self, sample_csv) -> None:
        ctx = MagicMock()
        ctx.params = {"file": sample_csv, "x": ["start"]}  # position 1 = end
        result = complete_date_column(ctx, [], "")
        # "end" contains end keyword, should come before "start"
        assert result.index("end") < result.index("start")

    def test_no_file_returns_empty(self) -> None:
        ctx = MagicMock()
        ctx.params = {"file": None, "x": []}
        result = complete_date_column(ctx, [], "")
        assert result == []

    def test_filters_by_prefix(self, sample_csv) -> None:
        ctx = MagicMock()
        ctx.params = {"file": sample_csv, "x": []}
        result = complete_date_column(ctx, [], "st")
        assert result == ["start"]

    def test_real_csv_start_position(self, real_csv) -> None:
        ctx = MagicMock()
        ctx.params = {"file": real_csv, "x": []}  # position 0 = start
        result = complete_date_column(ctx, [], "")
        start_cols = [c for c in result if "START" in c.upper()]
        other_cols = [c for c in result if "START" not in c.upper()]
        # All start-like columns should appear before non-start columns
        if start_cols and other_cols:
            assert result.index(start_cols[0]) < result.index(other_cols[0])

    def test_real_csv_end_position(self, real_csv) -> None:
        ctx = MagicMock()
        ctx.params = {"file": real_csv, "x": ["DH_PV_STARTDATUM"]}  # position 1 = end
        result = complete_date_column(ctx, [], "")
        end_cols = [c for c in result if "END" in c.upper() or "EIND" in c.upper()]
        assert len(end_cols) > 0
        # End-like columns should appear first
        assert result[0] in end_cols
