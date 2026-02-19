"""Tests for csvplot bubble matrix functionality."""

from __future__ import annotations

from pathlib import Path

import pytest

from csvplot.bubble import BubbleSpec, is_falsy, load_bubble_data

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

    def test_sort_preserves_total_rows(self, bubble_csv: Path) -> None:
        """Sort preserves total_rows count."""
        from csvplot.bubble import sort_bubble_spec

        spec = load_bubble_data(bubble_csv, cols=["feature_a"], y_col="name")
        sorted_spec = sort_bubble_spec(spec, "fill")
        assert sorted_spec.total_rows == spec.total_rows

    def test_sort_preserves_color_keys(self, bubble_csv: Path) -> None:
        """Sort keeps color_keys aligned with y_labels."""
        from csvplot.bubble import sort_bubble_spec

        cols = ["feature_a", "feature_b", "feature_c"]
        spec = load_bubble_data(bubble_csv, cols=cols, y_col="name", color_col="category")
        sorted_spec = sort_bubble_spec(spec, "fill")
        # eve is first (admin), dave is last (user)
        assert sorted_spec.color_keys[0] == "admin"
        assert sorted_spec.color_keys[-1] == "user"


class TestLoadBubbleGrouped:
    def test_basic_grouping(self, bubble_csv: Path) -> None:
        """Group by category and check fill-rates per group."""
        from csvplot.bubble import GroupedBubbleSpec, load_bubble_grouped

        cols = ["feature_a", "feature_b", "feature_c"]
        spec = load_bubble_grouped(bubble_csv, cols=cols, y_col="name", group_by="category")
        assert isinstance(spec, GroupedBubbleSpec)
        assert set(spec.group_labels) == {"admin", "user"}
        assert spec.col_names == cols
        # admin: alice, charlie, eve (3 rows)
        # feature_a: alice=T, charlie=T, eve=T → 3/3
        admin_idx = spec.group_labels.index("admin")
        assert spec.counts[admin_idx][0] == 3  # feature_a count
        assert spec.group_sizes[admin_idx] == 3

    def test_group_counts(self, bubble_csv: Path) -> None:
        """Verify absolute counts and group sizes."""
        from csvplot.bubble import load_bubble_grouped

        cols = ["feature_a", "feature_b", "feature_c"]
        spec = load_bubble_grouped(bubble_csv, cols=cols, y_col="name", group_by="category")
        # user: bob, dave (2 rows)
        user_idx = spec.group_labels.index("user")
        # feature_a: bob=F, dave=F → 0/2
        assert spec.counts[user_idx][0] == 0
        assert spec.group_sizes[user_idx] == 2

    def test_grouped_with_where(self, bubble_csv: Path) -> None:
        """--where filters apply before grouping."""
        from csvplot.bubble import load_bubble_grouped

        spec = load_bubble_grouped(
            bubble_csv,
            cols=["feature_a"],
            y_col="name",
            group_by="category",
            wheres=[("feature_a", "yes")],
        )
        # Only alice and eve match feature_a=yes, both admin
        assert "admin" in spec.group_labels
        admin_idx = spec.group_labels.index("admin")
        assert spec.group_sizes[admin_idx] == 2


class TestTransposeBubble:
    def test_transpose(self, bubble_csv: Path) -> None:
        """Transpose swaps rows and columns."""
        from csvplot.bubble import transpose_bubble_spec

        cols = ["feature_a", "feature_b", "feature_c"]
        spec = load_bubble_data(bubble_csv, cols=cols, y_col="name")
        tspec = transpose_bubble_spec(spec)
        # Original: 5 rows x 3 cols → transposed: 3 rows x 5 cols
        assert tspec.y_labels == ["feature_a", "feature_b", "feature_c"]
        assert tspec.col_names == ["alice", "bob", "charlie", "dave", "eve"]
        assert len(tspec.matrix) == 3
        assert len(tspec.matrix[0]) == 5
        # feature_a row: alice=T, bob=F, charlie=T, dave=F, eve=T
        assert tspec.matrix[0] == [True, False, True, False, True]

    def test_transpose_preserves_total_rows(self, bubble_csv: Path) -> None:
        from csvplot.bubble import transpose_bubble_spec

        spec = load_bubble_data(bubble_csv, cols=["feature_a"], y_col="name")
        tspec = transpose_bubble_spec(spec)
        assert tspec.total_rows == spec.total_rows


class TestColumnFillRates:
    def test_fill_rates(self, bubble_csv: Path) -> None:
        """Compute per-column fill-rate percentages."""
        from csvplot.bubble import column_fill_rates

        cols = ["feature_a", "feature_b", "feature_c"]
        spec = load_bubble_data(bubble_csv, cols=cols, y_col="name")
        rates = column_fill_rates(spec)
        # feature_a: alice=T, bob=F, charlie=T, dave=F, eve=T → 3/5=60%
        assert rates == {"feature_a": 60, "feature_b": 60, "feature_c": 40}

    def test_fill_rates_empty(self) -> None:
        from csvplot.bubble import column_fill_rates

        spec = BubbleSpec()
        rates = column_fill_rates(spec)
        assert rates == {}


# ---------------------------------------------------------------------------
# Encode (one-hot) tests
# ---------------------------------------------------------------------------

ENCODE_CSV = """\
name,role,active,team
alice,dev,yes,alpha
bob,pm,,alpha
charlie,dev,no,beta
dave,design,yes,beta
eve,pm,yes,alpha
frank,dev,,gamma
"""


@pytest.fixture
def encode_csv(tmp_path: Path) -> Path:
    p = tmp_path / "encode.csv"
    p.write_text(ENCODE_CSV)
    return p


class TestExpandCols:
    """Unit tests for _expand_cols helper."""

    def test_binary_column_expanded(self) -> None:
        from csvplot.bubble import _expand_cols

        # active has 2 unique non-empty values → col=value format (no empty bucket)
        unique = {"active": ["yes", "no"]}
        has_empty = {"active": True}
        result = _expand_cols(["active"], unique, has_empty)
        # Binary: no empty bucket even with empties
        assert result == [("onehot", "active", "yes"), ("onehot", "active", "no")]

    def test_categorical_column_expanded(self) -> None:
        from csvplot.bubble import _expand_cols

        # role has 3 unique values → categorical → one-hot
        unique = {"role": ["dev", "pm", "design"]}
        has_empty = {"role": False}
        result = _expand_cols(["role"], unique, has_empty)
        assert result == [
            ("onehot", "role", "dev"),
            ("onehot", "role", "pm"),
            ("onehot", "role", "design"),
        ]

    def test_empty_values_get_own_column(self) -> None:
        from csvplot.bubble import _expand_cols

        unique = {"role": ["dev", "pm", "design"]}
        has_empty = {"role": True}
        result = _expand_cols(["role"], unique, has_empty)
        assert ("onehot", "role", None) in result

    def test_mixed_columns(self) -> None:
        from csvplot.bubble import _expand_cols

        unique = {"active": ["yes", "no"], "role": ["dev", "pm", "design"]}
        has_empty = {"active": False, "role": False}
        result = _expand_cols(["active", "role"], unique, has_empty)
        assert result[0] == ("onehot", "active", "yes")
        assert result[1] == ("onehot", "active", "no")
        assert result[2] == ("onehot", "role", "dev")

    def test_single_unique_value_expanded(self) -> None:
        from csvplot.bubble import _expand_cols

        # Only 1 unique value → col=value format
        unique = {"flag": ["yes"]}
        has_empty = {"flag": False}
        result = _expand_cols(["flag"], unique, has_empty)
        assert result == [("onehot", "flag", "yes")]


class TestEncodeBubbleData:
    """Tests for load_bubble_data with encode=True."""

    def test_binary_column_expanded(self, encode_csv: Path) -> None:
        """Binary columns (<=2 unique) use col=value format with encode=True."""
        spec = load_bubble_data(encode_csv, cols=["active"], y_col="name", encode=True)
        # active has values: yes, "", no, yes, yes, ""
        # "no" is falsy → only "yes" is a unique non-falsy value → active=yes
        assert "active=yes" in spec.col_names
        yes_idx = spec.col_names.index("active=yes")
        # alice: active=yes → True
        assert spec.matrix[0][yes_idx] is True
        # bob: active="" → False
        assert spec.matrix[1][yes_idx] is False
        # charlie: active=no (falsy) → False
        assert spec.matrix[2][yes_idx] is False

    def test_categorical_column_expanded(self, encode_csv: Path) -> None:
        """Categorical columns (>2 unique) get one-hot encoded."""
        spec = load_bubble_data(encode_csv, cols=["role"], y_col="name", encode=True)
        assert "role=dev" in spec.col_names
        assert "role=pm" in spec.col_names
        assert "role=design" in spec.col_names

    def test_onehot_values_correct(self, encode_csv: Path) -> None:
        """One-hot encoded values match the original data."""
        spec = load_bubble_data(encode_csv, cols=["role"], y_col="name", encode=True)
        dev_idx = spec.col_names.index("role=dev")
        pm_idx = spec.col_names.index("role=pm")
        design_idx = spec.col_names.index("role=design")
        # alice is dev
        assert spec.matrix[0][dev_idx] is True
        assert spec.matrix[0][pm_idx] is False
        assert spec.matrix[0][design_idx] is False
        # dave is design
        assert spec.matrix[3][dev_idx] is False
        assert spec.matrix[3][design_idx] is True

    def test_empty_values_column(self, encode_csv: Path) -> None:
        """Columns with empty values get a col=(empty) column when categorical."""
        spec = load_bubble_data(encode_csv, cols=["team"], y_col="name", encode=True)
        # team has 3 unique values (alpha, beta, gamma) → categorical
        # no empties in team → no (empty) column
        assert "team=(empty)" not in spec.col_names
        assert "team=alpha" in spec.col_names

    def test_empty_values_column_present(self, encode_csv: Path) -> None:
        """Categorical column with empties gets (empty) column."""
        # active has empties but is binary (<=2 unique) so stays plain.
        # We need to test with a col that has >2 unique + empties.
        # Let's use role which has 3 unique and no empties in ENCODE_CSV.
        # We'll test via a separate CSV with empties in a categorical col.
        csv_text = "name,dept\nalice,eng\nbob,sales\ncharlie,hr\ndave,\n"
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_text)
            f.flush()
            spec = load_bubble_data(f.name, cols=["dept"], y_col="name", encode=True)
        assert "dept=(empty)" in spec.col_names
        empty_idx = spec.col_names.index("dept=(empty)")
        assert spec.matrix[3][empty_idx] is True  # dave has empty dept
        assert spec.matrix[0][empty_idx] is False  # alice has eng

    def test_mixed_binary_and_categorical(self, encode_csv: Path) -> None:
        """Mix of binary and categorical columns with encode=True."""
        spec = load_bubble_data(
            encode_csv, cols=["active", "role"], y_col="name", encode=True
        )
        # active: "no" is falsy, so only "yes" is a unique non-falsy value
        assert "active=yes" in spec.col_names
        # role is categorical → expanded
        assert "role=dev" in spec.col_names
        assert "role=pm" in spec.col_names
        assert "role=design" in spec.col_names

    def test_encode_false_no_expansion(self, encode_csv: Path) -> None:
        """With encode=False (default), no expansion happens."""
        spec = load_bubble_data(encode_csv, cols=["role"], y_col="name")
        assert spec.col_names == ["role"]

    def test_encode_with_top(self, encode_csv: Path) -> None:
        """--top filters after encoding (on expanded columns)."""
        spec = load_bubble_data(
            encode_csv, cols=["role"], y_col="name", encode=True, top=2
        )
        assert len(spec.col_names) == 2

    def test_encode_with_where(self, encode_csv: Path) -> None:
        """--where applies before encoding."""
        spec = load_bubble_data(
            encode_csv,
            cols=["role"],
            y_col="name",
            encode=True,
            wheres=[("team", "alpha")],
        )
        # alpha team: alice(dev), bob(pm), eve(pm) — only 2 unique roles
        # <=2 unique → col=value format
        assert "role=dev" in spec.col_names
        assert "role=pm" in spec.col_names
        assert len(spec.y_labels) == 3


class TestEncodeGrouped:
    """Tests for load_bubble_grouped with encode=True."""

    def test_grouped_encode_expands(self, encode_csv: Path) -> None:
        from csvplot.bubble import load_bubble_grouped

        spec = load_bubble_grouped(
            encode_csv, cols=["role"], y_col="name", group_by="team", encode=True
        )
        assert "role=dev" in spec.col_names
        assert "role=pm" in spec.col_names
        assert "role=design" in spec.col_names

    def test_grouped_encode_counts(self, encode_csv: Path) -> None:
        from csvplot.bubble import load_bubble_grouped

        spec = load_bubble_grouped(
            encode_csv, cols=["role"], y_col="name", group_by="team", encode=True
        )
        # alpha team: alice(dev), bob(pm), eve(pm)
        alpha_idx = spec.group_labels.index("alpha")
        dev_idx = spec.col_names.index("role=dev")
        pm_idx = spec.col_names.index("role=pm")
        assert spec.counts[alpha_idx][dev_idx] == 1
        assert spec.counts[alpha_idx][pm_idx] == 2
