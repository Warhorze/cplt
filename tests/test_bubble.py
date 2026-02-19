"""Tests for csvplot bubble matrix functionality."""

from __future__ import annotations

from pathlib import Path

import pytest

from csvplot.bubble import is_falsy, load_bubble_data

BUBBLE_CSV = """\
name,feature_a,feature_b,feature_c,category
alice,yes,,true,admin
bob,0,1,false,user
charlie,active,present,,admin
dave,,0,no,user
eve,yes,1,YES,admin
"""


@pytest.fixture
def bubble_csv(tmp_path: Path) -> Path:
    p = tmp_path / "bubble.csv"
    p.write_text(BUBBLE_CSV)
    return p


class TestIsFalsy:
    @pytest.mark.parametrize(
        "value",
        ["", "0", "false", "False", "FALSE", "no", "No", "null", "none", "na", "nan", "NaN"],
    )
    def test_falsy_values(self, value: str) -> None:
        assert is_falsy(value) is True

    @pytest.mark.parametrize("value", ["yes", "1", "true", "active", "present", "hello"])
    def test_truthy_values(self, value: str) -> None:
        assert is_falsy(value) is False


class TestLoadBubbleData:
    def test_basic_loading(self, bubble_csv: Path) -> None:
        cols = ["feature_a", "feature_b", "feature_c"]
        spec = load_bubble_data(bubble_csv, cols=cols, y_col="name")
        assert spec.y_labels == ["alice", "bob", "charlie", "dave", "eve"]
        assert spec.col_names == ["feature_a", "feature_b", "feature_c"]
        assert len(spec.matrix) == 5  # 5 rows
        assert len(spec.matrix[0]) == 3  # 3 columns

    def test_matrix_values(self, bubble_csv: Path) -> None:
        cols = ["feature_a", "feature_b", "feature_c"]
        spec = load_bubble_data(bubble_csv, cols=cols, y_col="name")
        # alice: yes=T, ""=F, true=T
        assert spec.matrix[0] == [True, False, True]
        # bob: 0=F, 1=T, false=F
        assert spec.matrix[1] == [False, True, False]
        # dave: ""=F, 0=F, no=F
        assert spec.matrix[3] == [False, False, False]

    def test_with_where_filter(self, bubble_csv: Path) -> None:
        spec = load_bubble_data(
            bubble_csv,
            cols=["feature_a", "feature_b"],
            y_col="name",
            wheres=[("category", "admin")],
        )
        assert spec.y_labels == ["alice", "charlie", "eve"]

    def test_head_limits_rows(self, bubble_csv: Path) -> None:
        spec = load_bubble_data(bubble_csv, cols=["feature_a"], y_col="name", max_rows=2)
        assert len(spec.y_labels) == 2

    def test_missing_column_raises_with_available_columns(self, bubble_csv: Path) -> None:
        with pytest.raises(KeyError, match="Available:"):
            load_bubble_data(bubble_csv, cols=["nonexistent"], y_col="name")

    def test_top_by_fill_rate(self, bubble_csv: Path) -> None:
        spec = load_bubble_data(
            bubble_csv,
            cols=["feature_a", "feature_b", "feature_c"],
            y_col="name",
            top=2,
        )
        # feature_a has 3 truthy, feature_b has 2 truthy, feature_c has 2 truthy
        # top 2 by fill rate: feature_a (3/5), then feature_b or feature_c (2/5 each)
        assert len(spec.col_names) == 2
        assert spec.col_names[0] == "feature_a"

    def test_color_column(self, bubble_csv: Path) -> None:
        spec = load_bubble_data(
            bubble_csv,
            cols=["feature_a"],
            y_col="name",
            color_col="category",
        )
        assert spec.color_keys == ["admin", "user", "admin", "user", "admin"]

    def test_sample_rows(self, bubble_csv: Path) -> None:
        spec = load_bubble_data(
            bubble_csv,
            cols=["feature_a"],
            y_col="name",
            sample_n=3,
        )
        assert len(spec.y_labels) == 3
        assert spec.total_rows == 5


class TestSortBubble:
    def test_sort_fill_descending(self, bubble_csv: Path) -> None:
        """Sort by fill-rate descending: most complete rows first."""
        from csvplot.bubble import sort_bubble_spec

        cols = ["feature_a", "feature_b", "feature_c"]
        spec = load_bubble_data(bubble_csv, cols=cols, y_col="name")
        sorted_spec = sort_bubble_spec(spec, "fill")
        # eve has 3/3, alice has 2/3, charlie has 2/3, bob has 1/3, dave has 0/3
        assert sorted_spec.y_labels[0] == "eve"
        assert sorted_spec.y_labels[-1] == "dave"

    def test_sort_fill_ascending(self, bubble_csv: Path) -> None:
        """Sort by fill-rate ascending: least complete rows first."""
        from csvplot.bubble import sort_bubble_spec

        cols = ["feature_a", "feature_b", "feature_c"]
        spec = load_bubble_data(bubble_csv, cols=cols, y_col="name")
        sorted_spec = sort_bubble_spec(spec, "fill-asc")
        assert sorted_spec.y_labels[0] == "dave"
        assert sorted_spec.y_labels[-1] == "eve"

    def test_sort_name(self, bubble_csv: Path) -> None:
        """Sort alphabetically by y-label."""
        from csvplot.bubble import sort_bubble_spec

        cols = ["feature_a", "feature_b", "feature_c"]
        spec = load_bubble_data(bubble_csv, cols=cols, y_col="name")
        sorted_spec = sort_bubble_spec(spec, "name")
        assert sorted_spec.y_labels == ["alice", "bob", "charlie", "dave", "eve"]

    def test_sort_preserves_color_keys(self, bubble_csv: Path) -> None:
        """Sort keeps color_keys aligned with y_labels."""
        from csvplot.bubble import sort_bubble_spec

        cols = ["feature_a", "feature_b", "feature_c"]
        spec = load_bubble_data(bubble_csv, cols=cols, y_col="name", color_col="category")
        sorted_spec = sort_bubble_spec(spec, "fill")
        # eve is first (admin), dave is last (user)
        assert sorted_spec.color_keys[0] == "admin"
        assert sorted_spec.color_keys[-1] == "user"
