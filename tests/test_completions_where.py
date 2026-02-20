"""Tests for --where value completion and improved autocomplete."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

import click
import pytest

from csvplot.completions import _BASH_EQ_SAFE, complete_where, match_values

WHERE_CSV = """\
name,status,region
alice,open,north
bob,closed,south
charlie,open,north
dave,pending,south
eve,Open,west
frank,,east
"""


@pytest.fixture
def where_csv(tmp_path: Path) -> Path:
    p = tmp_path / "where.csv"
    p.write_text(WHERE_CSV)
    return p


class TestMatchValues:
    def test_prefix_match(self) -> None:
        values = ["open", "closed", "option", "pending"]
        result = match_values("op", values)
        assert result == ["open", "option"]

    def test_substring_fallback(self) -> None:
        values = ["open", "closed", "option", "reopened"]
        result = match_values("pen", values)
        # "open" and "reopened" contain "pen", "pending" not in list
        assert "open" in result
        assert "reopened" in result

    def test_difflib_typo_fallback(self) -> None:
        values = ["open", "closed", "pending"]
        result = match_values("opne", values)
        assert "open" in result

    def test_empty_incomplete_returns_all(self) -> None:
        values = ["open", "closed", "pending"]
        result = match_values("", values)
        assert result == ["open", "closed", "pending"]

    def test_no_match_returns_empty(self) -> None:
        values = ["open", "closed", "pending"]
        result = match_values("zzzzz", values)
        assert result == []

    def test_case_insensitive(self) -> None:
        values = ["Open", "CLOSED", "pending"]
        result = match_values("op", values)
        assert "Open" in result


class TestCompleteWhere:
    @staticmethod
    def _ctx(params: dict[str, Any]) -> click.Context:
        mock = MagicMock()
        mock.params = params
        return cast(click.Context, mock)

    def test_empty_incomplete_suggests_columns(self, where_csv: Path) -> None:
        ctx = self._ctx({"file": where_csv, "x": ["status"]})
        result = complete_where(ctx, [], "")
        # Should suggest column=value format, with last --x column pre-filled
        assert any("status=" in r for r in result)

    def test_with_col_prefix_suggests_values(self, where_csv: Path) -> None:
        ctx = self._ctx({"file": where_csv, "x": ["status"]})
        result = complete_where(ctx, [], "status=")
        assert any("open" in r.lower() for r in result)
        assert "status=(empty)" in result

    def test_with_partial_value(self, where_csv: Path) -> None:
        ctx = self._ctx({"file": where_csv, "x": ["status"]})
        result = complete_where(ctx, [], "status=op")
        # Should match "open" and "Open"
        assert any("open" in r.lower() for r in result)

    def test_with_col_prefix_case_insensitive(self, where_csv: Path) -> None:
        ctx = self._ctx({"file": where_csv, "x": ["status"]})
        result = complete_where(ctx, [], "STATUS=op")
        # Runtime filtering is case-insensitive; completion should match that behavior.
        assert any(r.startswith("status=") for r in result)
        assert any("open" in r.lower() for r in result)

    def test_no_file_returns_empty(self) -> None:
        ctx = self._ctx({"file": None})
        result = complete_where(ctx, [], "")
        assert result == []

    def test_context_from_y(self, where_csv: Path) -> None:
        ctx = self._ctx({"file": where_csv, "y": ["region"], "x": []})
        result = complete_where(ctx, [], "")
        assert any("region=" in r for r in result)

    def test_context_column_case_insensitive(self, where_csv: Path) -> None:
        ctx = self._ctx({"file": where_csv, "y": ["STATUS"], "x": []})
        result = complete_where(ctx, [], "")
        assert any(r.startswith("status=") for r in result)

    def test_malformed_csv_no_crash(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.csv"
        bad.write_text("this is not\nvalid csv \x00 data")
        ctx = self._ctx({"file": bad})
        result = complete_where(ctx, [], "")
        assert isinstance(result, list)

    def test_stage1_only_col_prefix_no_values(self, where_csv: Path) -> None:
        """Stage 1 (no '=' typed) must return only COL= tokens, never COL=value.

        Shells strip the common prefix from display, so after the user picks
        'status=' and types it, the next tab shows 'open', 'closed', … — the
        shell hides the 'status=' prefix.  Mixing full 'status=open' entries in
        stage 1 with bare 'region=' entries is confusing.
        """
        ctx = self._ctx({"file": where_csv, "x": ["status"]})
        result = complete_where(ctx, [], "")
        assert all(r.endswith("=") for r in result), (
            f"Stage-1 results must all end with '=', got: {result}"
        )

    def test_stage1_context_column_appears_first(self, where_csv: Path) -> None:
        """Context column (from --y) should be listed before other columns."""
        ctx = self._ctx({"file": where_csv, "y": ["region"], "x": []})
        result = complete_where(ctx, [], "")
        assert result, "Expected non-empty suggestions"
        assert result[0] == "region=", (
            f"Context column 'region=' should be first, got: {result[0]!r}"
        )

    def test_where_param_used_as_context_for_where_not(self, where_csv: Path) -> None:
        """When --where already names a column, --where-not completion should
        surface that same column first (natural include/exclude flow on one column).
        """
        ctx = self._ctx({"file": where_csv, "where": ["status=open"], "x": [], "y": []})
        result = complete_where(ctx, [], "")
        assert result, "Expected non-empty suggestions"
        assert result[0] == "status=", (
            f"Column from --where should be context for --where-not, got: {result[0]!r}"
        )


class TestBashCompletionScript:
    """Verify the patched bash completion script handles nospace correctly."""

    def test_nospace_option_present(self) -> None:
        """Script must use -o nospace so bash doesn't add a trailing space after COL=."""
        assert "-o nospace" in _BASH_EQ_SAFE

    def test_appends_space_to_non_eq_completions(self) -> None:
        """Script must append a space to completions that don't end with '='
        so that normal argument separation works after value completions.
        """
        # The script should contain logic to add a trailing space to
        # completions that don't end with '='
        assert '" "' in _BASH_EQ_SAFE or "' '" in _BASH_EQ_SAFE
