"""Cross-stage option combination tests for the bubble command.

Phase 1 tests lock in current working behavior.
Phase 2 tests (xfail) define desired behavior for broken/missing combinations.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.ux.conftest import invoke

# ============================================================================
# Phase 1: Tests that pass against current code
# ============================================================================


class TestBubbleCrossStageGreen:
    """Combinations that work correctly today."""

    def test_head_plus_where(self, ux_bubble_csv: Path) -> None:
        """Stage 1→2: --head limits rows kept, --where filters the stream."""
        result = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--y", "name",
            "--head", "3", "--where", "category=frontend",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # Where filters to frontend rows, head keeps first 3 of those
        data_lines = [
            ln for ln in result.stdout.split("\n")
            if "|" in ln and "cols:" not in ln and "fill:" not in ln
        ]
        labels = [ln.split("|")[0].strip() for ln in data_lines]
        assert len(labels) == 3
        # Remaining frontend rows exist beyond head=3
        assert "Showing 3 of" in result.stdout

    def test_where_plus_encode(self, encode_bubble_csv: Path) -> None:
        """Stage 2→4: --where filters before encode sees cardinality."""
        # Filter to team=alpha (alice=dev, bob=pm, eve=pm) → role has 2 unique (dev, pm)
        # With 2 unique, encode treats as binary → plain column name
        result = invoke(
            "bubble", "-f", str(encode_bubble_csv),
            "--cols", "role", "--y", "name",
            "--where", "team=alpha", "--encode",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # 2 unique values in filtered set → binary → plain "role"
        assert "role" in result.stdout
        assert "role=" not in result.stdout

    def test_where_plus_encode_categorical(self, encode_bubble_csv: Path) -> None:
        """Stage 2→4: without filter, full cardinality triggers one-hot."""
        result = invoke(
            "bubble", "-f", str(encode_bubble_csv),
            "--cols", "role", "--y", "name",
            "--encode",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # 3 unique values → categorical → one-hot
        assert "role=dev" in result.stdout
        assert "role=pm" in result.stdout
        assert "role=design" in result.stdout

    def test_sample_plus_encode(self, encode_bubble_csv: Path) -> None:
        """Stage 3→4: --sample limits rows before encode scans cardinality."""
        result = invoke(
            "bubble", "-f", str(encode_bubble_csv),
            "--cols", "role", "--y", "name",
            "--sample", "3", "--encode",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # With 3 sampled rows, role might have <=2 unique → binary, or 3 → categorical
        # Either way it should work without error
        data_lines = [
            ln for ln in result.stdout.split("\n")
            if "|" in ln and "cols:" not in ln and "fill:" not in ln
        ]
        assert len(data_lines) == 3

    def test_encode_plus_sort(self, encode_bubble_csv: Path) -> None:
        """Stage 4→6: --sort works on encoded columns."""
        result = invoke(
            "bubble", "-f", str(encode_bubble_csv),
            "--cols", "role", "--y", "name",
            "--encode", "--sort", "fill",
            "--format", "compact",
        )
        assert result.exit_code == 0
        assert "role=" in result.stdout

    def test_encode_plus_transpose(self, encode_bubble_csv: Path) -> None:
        """Stage 4→6: --transpose with encoded columns."""
        result = invoke(
            "bubble", "-f", str(encode_bubble_csv),
            "--cols", "role", "--y", "name",
            "--encode", "--transpose",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # Encoded col names (role=dev etc.) should now be row labels
        assert "role=dev" in result.stdout

    def test_where_plus_encode_plus_group_by(self, encode_bubble_csv: Path) -> None:
        """Stage 2→4→5: filter → encode → group-by."""
        result = invoke(
            "bubble", "-f", str(encode_bubble_csv),
            "--cols", "role", "--y", "name",
            "--where", "active=yes",
            "--encode", "--group-by", "team",
            "--format", "compact",
        )
        assert result.exit_code == 0
        assert "%" in result.stdout

    def test_head_plus_where_plus_encode(self, encode_bubble_csv: Path) -> None:
        """Stage 1→2→4: head → filter → encode."""
        result = invoke(
            "bubble", "-f", str(encode_bubble_csv),
            "--cols", "role", "--y", "name",
            "--head", "4", "--where", "active=yes",
            "--encode",
            "--format", "compact",
        )
        assert result.exit_code == 0

    def test_where_plus_encode_plus_top(self, encode_bubble_csv: Path) -> None:
        """Stage 2→4: filter → encode → top N selects highest fill-rate encoded cols."""
        result = invoke(
            "bubble", "-f", str(encode_bubble_csv),
            "--cols", "role", "--y", "name",
            "--encode", "--top", "2",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # 3 encoded cols (role=dev, role=pm, role=design), top 2 keeps highest fill
        col_line = [ln for ln in result.stdout.split("\n") if ln.startswith("cols:")]
        assert len(col_line) == 1
        col_count = col_line[0].count("|") + 1
        assert col_count == 2

    def test_option_order_sort_encode(self, encode_bubble_csv: Path) -> None:
        """Option order must not matter: --sort before --encode vs after."""
        result_a = invoke(
            "bubble", "-f", str(encode_bubble_csv),
            "--cols", "role", "--y", "name",
            "--sort", "fill", "--encode",
            "--format", "compact",
        )
        result_b = invoke(
            "bubble", "-f", str(encode_bubble_csv),
            "--cols", "role", "--y", "name",
            "--encode", "--sort", "fill",
            "--format", "compact",
        )
        assert result_a.exit_code == 0
        assert result_b.exit_code == 0
        assert result_a.stdout == result_b.stdout

    def test_option_order_transpose_sort(self, ux_bubble_csv: Path) -> None:
        """Option order must not matter: --transpose before --sort vs after."""
        result_a = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--cols", "feat_b",
            "--y", "name",
            "--transpose", "--sort", "fill",
            "--format", "compact",
        )
        result_b = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--cols", "feat_b",
            "--y", "name",
            "--sort", "fill", "--transpose",
            "--format", "compact",
        )
        assert result_a.exit_code == 0
        assert result_b.exit_code == 0
        assert result_a.stdout == result_b.stdout


# ============================================================================
# Phase 2: Tests for desired behavior (xfail — currently broken/missing)
# ============================================================================


class TestBubbleCrossStageBroken:
    """Combinations that are currently broken or missing."""

    @pytest.mark.xfail(reason="group-by takes separate code path, sort is ignored")
    def test_group_by_plus_sort(self, ux_bubble_csv: Path) -> None:
        """Stage 5→6: --group-by + --sort should sort groups by fill-rate."""
        base = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--cols", "feat_b", "--cols", "feat_c",
            "--y", "name", "--group-by", "category",
            "--format", "compact",
        )
        sorted_result = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--cols", "feat_b", "--cols", "feat_c",
            "--y", "name", "--group-by", "category",
            "--sort", "fill",
            "--format", "compact",
        )
        assert base.exit_code == 0
        assert sorted_result.exit_code == 0
        # Sort should reorder groups — output must differ from unsorted
        assert base.stdout != sorted_result.stdout

    @pytest.mark.xfail(reason="group-by takes separate code path, transpose is ignored")
    def test_group_by_plus_transpose(self, ux_bubble_csv: Path) -> None:
        """Stage 5→6: --group-by + --transpose should transpose the group table."""
        base = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--cols", "feat_b",
            "--y", "name", "--group-by", "category",
            "--format", "compact",
        )
        transposed = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--cols", "feat_b",
            "--y", "name", "--group-by", "category",
            "--transpose",
            "--format", "compact",
        )
        assert base.exit_code == 0
        assert transposed.exit_code == 0
        # Transpose should swap the layout — output must differ
        assert base.stdout != transposed.stdout

    @pytest.mark.xfail(reason="group-by ignores --sample, should error")
    def test_group_by_plus_sample_errors(self, ux_bubble_csv: Path) -> None:
        """Stage 3+5: --group-by + --sample should produce an error."""
        result = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--y", "name",
            "--group-by", "category", "--sample", "3",
            "--format", "compact",
        )
        assert result.exit_code != 0
        assert "sample" in result.stdout.lower() or "sample" in (result.stderr or "").lower()

    @pytest.mark.xfail(reason="group-by ignores --head, should pass through to limit input")
    def test_group_by_plus_head(self, ux_bubble_csv: Path) -> None:
        """Stage 1+5: --group-by + --head should limit input rows."""
        full = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--y", "name",
            "--group-by", "category",
            "--format", "compact",
        )
        limited = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--y", "name",
            "--group-by", "category", "--head", "3",
            "--format", "compact",
        )
        assert full.exit_code == 0
        assert limited.exit_code == 0
        # With head=3, only first 3 rows are read → fewer rows in group aggregation
        # The total rows count should differ
        assert full.stdout != limited.stdout

    @pytest.mark.xfail(reason="binary encode currently uses plain col name, should use col=value")
    def test_encode_binary_col_value_format(self, ux_bubble_csv: Path) -> None:
        """Stage 4: binary encode (<=2 unique) should use col=value format with 1/0."""
        result = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "category", "--y", "name",
            "--encode",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # Binary (2 unique: frontend, backend) should produce category=frontend, category=backend
        assert "category=frontend" in result.stdout or "category=backend" in result.stdout

    @pytest.mark.xfail(reason="encode auto-cap at 20 not implemented")
    def test_encode_auto_cap_at_20(self, high_card_bubble_csv: Path) -> None:
        """Stage 4: >20 encoded columns should auto-cap at 20 with warning."""
        result = invoke(
            "bubble", "-f", str(high_card_bubble_csv),
            "--cols", "tag", "--y", "name",
            "--encode",
            "--format", "compact",
        )
        assert result.exit_code == 0
        # 25 unique values → one-hot → 25 columns → should auto-cap at 20
        col_line = [ln for ln in result.stdout.split("\n") if ln.startswith("cols:")]
        assert len(col_line) == 1
        col_count = col_line[0].count("|") + 1
        assert col_count <= 20

    @pytest.mark.xfail(reason="--no-encode toggle should be removed, just use --encode flag")
    def test_no_encode_flag_removed(self, ux_bubble_csv: Path) -> None:
        """--no-encode should not be a valid option (dead toggle)."""
        result = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--y", "name",
            "--no-encode",
            "--format", "compact",
        )
        # Should fail because --no-encode is removed
        assert result.exit_code != 0

    @pytest.mark.xfail(reason="--no-transpose toggle should be removed, just use --transpose flag")
    def test_no_transpose_flag_removed(self, ux_bubble_csv: Path) -> None:
        """--no-transpose should not be a valid option (dead toggle)."""
        result = invoke(
            "bubble", "-f", str(ux_bubble_csv),
            "--cols", "feat_a", "--y", "name",
            "--no-transpose",
            "--format", "compact",
        )
        # Should fail because --no-transpose is removed
        assert result.exit_code != 0
