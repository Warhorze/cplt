"""Tests for compact token-efficient plot output."""

from __future__ import annotations

from datetime import datetime

from cplt.bubble import BubbleSpec
from cplt.compact import (
    compact_bar,
    compact_bubble,
    compact_line,
    compact_summarise,
    compact_timeline,
    rle_encode,
)
from cplt.models import BarSpec, Dot, LineSpec, PlotSpec, Segment, VLine
from cplt.summarise import ColumnSummary


class TestRleEncode:
    def test_empty(self):
        assert rle_encode([]) == ""

    def test_single_char(self):
        assert rle_encode(["█"]) == "█"

    def test_repeated(self):
        assert rle_encode(["█", "█", "█"]) == "█3"

    def test_mixed(self):
        assert rle_encode(["█", "█", "·", "·", "·", "█"]) == "█2·3█"

    def test_alternating(self):
        assert rle_encode(["█", "·", "█", "·"]) == "█·█·"

    def test_long_run(self):
        assert rle_encode(["·"] * 50) == "·50"

    def test_multiple_groups(self):
        chars = ["█"] * 5 + ["·"] * 3 + ["#"] * 2
        assert rle_encode(chars) == "█5·3#2"


def _dt(month: int, day: int = 1) -> datetime:
    return datetime(2024, month, day)


class TestCompactTimeline:
    def test_single_segment_full_span(self):
        """A segment spanning the full range fills the entire width."""
        spec = PlotSpec(
            segments=[Segment(0, 0, "A", _dt(1), _dt(6))],
            title="Test",
        )
        out = compact_timeline(spec, width=10)
        assert "[COMPACT:timeline] Test" in out
        lines = out.strip().split("\n")
        # Find the row line for label A
        row_line = [ln for ln in lines if ln.startswith("A")][0]
        assert "|█10|" in row_line

    def test_partial_fill(self):
        """A segment covering half the range fills roughly half the width."""
        spec = PlotSpec(
            segments=[Segment(0, 0, "A", _dt(1), _dt(4))],
            title="Test",
            view_start=_dt(1),
            view_end=_dt(7),
        )
        out = compact_timeline(spec, width=12)
        lines = out.strip().split("\n")
        row_line = [ln for ln in lines if ln.startswith("A")][0]
        # Extract content between pipes
        inner = row_line.split("|")[1]
        # Should have some █ and some ·
        assert "█" in inner
        assert "·" in inner

    def test_multiple_labels(self):
        """Multiple y-labels produce separate rows."""
        spec = PlotSpec(
            segments=[
                Segment(0, 0, "A", _dt(1), _dt(3)),
                Segment(1, 0, "B", _dt(2), _dt(5)),
            ],
            title="Multi",
        )
        out = compact_timeline(spec, width=20)
        lines = out.strip().split("\n")
        a_lines = [ln for ln in lines if ln.startswith("A")]
        b_lines = [ln for ln in lines if ln.startswith("B")]
        assert len(a_lines) == 1
        assert len(b_lines) == 1

    def test_vlines_section(self):
        """Vertical reference lines appear in the output."""
        spec = PlotSpec(
            segments=[Segment(0, 0, "A", _dt(1), _dt(6))],
            vlines=[VLine(date=_dt(3, 15), label="deadline")],
            title="Test",
        )
        out = compact_timeline(spec, width=20)
        assert "vlines:" in out
        assert "deadline" in out

    def test_view_window(self):
        """view_start/view_end control the x-axis range."""
        spec = PlotSpec(
            segments=[Segment(0, 0, "A", _dt(1), _dt(6))],
            view_start=_dt(3),
            view_end=_dt(6),
            title="Windowed",
        )
        out = compact_timeline(spec, width=20)
        assert "2024-03-01" in out
        assert "2024-06-01" in out

    def test_multi_layer(self):
        """Multiple layers use different characters."""
        spec = PlotSpec(
            segments=[
                Segment(0, 0, "A", _dt(1), _dt(6)),
                Segment(0, 1, "A", _dt(2), _dt(5)),
            ],
            title="Layers",
        )
        out = compact_timeline(spec, width=20)
        lines = out.strip().split("\n")
        a_lines = [ln for ln in lines if ln.startswith("A")]
        # Layer 0 uses █, layer 1 uses #
        assert any("█" in ln for ln in a_lines)
        assert any("#" in ln for ln in a_lines)

    def test_sub_rows(self):
        """Multiple segments with same y_label but different row_index get separate rows."""
        spec = PlotSpec(
            segments=[
                Segment(0, 0, "A", _dt(1), _dt(3)),
                Segment(1, 0, "A", _dt(4), _dt(6)),
            ],
            title="SubRows",
        )
        out = compact_timeline(spec, width=20)
        lines = out.strip().split("\n")
        a_lines = [ln for ln in lines if ln.startswith("A")]
        assert len(a_lines) == 2

    def test_empty_segments(self):
        """Empty segment list produces minimal output."""
        spec = PlotSpec(segments=[], title="Empty")
        out = compact_timeline(spec, width=20)
        assert "[COMPACT:timeline] Empty" in out

    def test_x_range_header(self):
        """Output includes x-axis range info."""
        spec = PlotSpec(
            segments=[Segment(0, 0, "A", _dt(1), _dt(6))],
            title="Test",
        )
        out = compact_timeline(spec, width=20)
        assert "x:" in out
        assert "w=20" in out

    def test_legend_with_color(self):
        """When color_col_name is set, legend appears."""
        spec = PlotSpec(
            segments=[
                Segment(0, 0, "A", _dt(1), _dt(6), color_key="Active"),
                Segment(1, 0, "B", _dt(2), _dt(5), color_key="Done"),
            ],
            title="Colored",
            color_col_name="status",
        )
        out = compact_timeline(spec, width=20)
        assert "legend:" in out
        assert "Active" in out


class TestCompactTimelineDots:
    def test_dot_renders_as_diamond(self):
        """A dot renders as ◆ at the correct position."""
        spec = PlotSpec(
            segments=[Segment(0, 0, "A", _dt(1), _dt(6))],
            dots=[Dot(row_index=0, layer=0, y_label="A", date=_dt(3))],
            dot_col_names=["due"],
            title="DotTest",
        )
        out = compact_timeline(spec, width=10)
        lines = out.strip().split("\n")
        a_lines = [ln for ln in lines if ln.startswith("A")]
        assert len(a_lines) == 1
        assert "◆" in a_lines[0]

    def test_dot_position_maps_correctly(self):
        """Dot at the start of the range maps to position 0."""
        spec = PlotSpec(
            segments=[Segment(0, 0, "A", _dt(1), _dt(6))],
            dots=[Dot(row_index=0, layer=0, y_label="A", date=_dt(1))],
            dot_col_names=["due"],
            title="DotPos",
        )
        out = compact_timeline(spec, width=10)
        lines = out.strip().split("\n")
        a_line = [ln for ln in lines if ln.startswith("A")][0]
        inner = a_line.split("|")[1]
        # Diamond should be at the first position (overlaying segment)
        assert inner[0] == "◆"

    def test_dot_without_segment_at_label(self):
        """Dots for a y_label that has segments still render on the segment row."""
        spec = PlotSpec(
            segments=[Segment(0, 0, "A", _dt(1), _dt(3))],
            dots=[Dot(row_index=0, layer=0, y_label="A", date=_dt(5))],
            dot_col_names=["due"],
            title="DotOutside",
            view_end=_dt(6),
        )
        out = compact_timeline(spec, width=10)
        lines = out.strip().split("\n")
        a_lines = [ln for ln in lines if ln.startswith("A")]
        assert len(a_lines) == 1
        assert "◆" in a_lines[0]

    def test_dot_col_names_in_legend(self):
        """Dot column names appear in the output."""
        spec = PlotSpec(
            segments=[Segment(0, 0, "A", _dt(1), _dt(6))],
            dots=[Dot(row_index=0, layer=0, y_label="A", date=_dt(3))],
            dot_col_names=["due_date"],
            title="DotLegend",
        )
        out = compact_timeline(spec, width=10)
        assert "due_date" in out


class TestCompactBar:
    def test_single_bar(self):
        spec = BarSpec(labels=["A"], values=[10.0], title="Bar Test")
        out = compact_bar(spec, width=20)
        assert "[COMPACT:bar] Bar Test" in out
        assert "A" in out
        # Full bar since it's the max value
        assert "|█20|" in out
        assert "10" in out

    def test_scaling(self):
        """Bars scale proportionally to max value."""
        spec = BarSpec(labels=["A", "B"], values=[20.0, 10.0], title="Scale")
        out = compact_bar(spec, width=20)
        lines = out.strip().split("\n")
        a_line = [ln for ln in lines if ln.strip().startswith("A")][0]
        b_line = [ln for ln in lines if ln.strip().startswith("B")][0]
        assert "|█20|" in a_line
        assert "|█10·10|" in b_line

    def test_zero_value(self):
        """Zero value produces empty bar."""
        spec = BarSpec(labels=["A", "B"], values=[10.0, 0.0], title="Zero")
        out = compact_bar(spec, width=10)
        lines = out.strip().split("\n")
        b_line = [ln for ln in lines if ln.strip().startswith("B")][0]
        assert "|·10|" in b_line

    def test_title(self):
        spec = BarSpec(labels=["X"], values=[5.0], title="My Title")
        out = compact_bar(spec, width=10)
        assert "[COMPACT:bar] My Title" in out


class TestCompactLine:
    def test_single_series(self):
        spec = LineSpec(
            x_values=["a", "b", "c", "d"],
            y_series={"temp": [0.0, 10.0, 20.0, 30.0]},
            title="Line Test",
        )
        out = compact_line(spec, width=4)
        assert "[COMPACT:line] Line Test" in out
        assert "temp:" in out
        # Should have sparkline chars
        assert "▁" in out
        assert "█" in out

    def test_min_max_annotation(self):
        """Output includes min/max values formatted with g format."""
        spec = LineSpec(
            x_values=["a", "b", "c"],
            y_series={"temp": [5.0, 15.0, 25.0]},
            title="Annotated",
        )
        out = compact_line(spec, width=3)
        assert "min=5" in out
        assert "max=25" in out

    def test_min_max_rounds_long_decimals(self):
        """Long decimal values are rounded in min/max annotation."""
        spec = LineSpec(
            x_values=["a", "b", "c"],
            y_series={"temp": [1.23456789, 5.0, 9.87654321]},
            title="Rounded",
        )
        out = compact_line(spec, width=3)
        assert "min=1.235" in out
        assert "max=9.877" in out

    def test_multiple_series(self):
        """Multiple series produce separate sparkline rows."""
        spec = LineSpec(
            x_values=["a", "b"],
            y_series={"temp": [10.0, 20.0], "hum": [40.0, 80.0]},
            title="Multi",
        )
        out = compact_line(spec, width=2)
        assert "temp:" in out
        assert "hum:" in out

    def test_constant_values(self):
        """All same values should produce mid-level sparkline."""
        spec = LineSpec(
            x_values=["a", "b", "c"],
            y_series={"flat": [10.0, 10.0, 10.0]},
            title="Flat",
        )
        out = compact_line(spec, width=3)
        assert "flat:" in out
        # All same value → all same sparkline char
        lines = out.strip().split("\n")
        flat_line = [ln for ln in lines if ln.startswith("flat:")][0]
        # Extract sparkline between colon and paren
        sparkline = flat_line.split(":")[1].strip().split(" (")[0].strip()
        assert len(set(sparkline)) == 1  # all same character

    def test_downsampling(self):
        """When data exceeds width, it downsamples by averaging."""
        spec = LineSpec(
            x_values=[str(i) for i in range(100)],
            y_series={"big": [float(i) for i in range(100)]},
            title="Down",
        )
        out = compact_line(spec, width=10)
        lines = out.strip().split("\n")
        big_line = [ln for ln in lines if ln.startswith("big:")][0]
        sparkline = big_line.split(":")[1].strip().split(" (")[0].strip()
        assert len(sparkline) == 10

    def test_x_range_with_dates(self):
        """Date x-values show range in header."""
        spec = LineSpec(
            x_values=["2024-01-01", "2024-01-05", "2024-01-10"],
            y_series={"v": [1.0, 2.0, 3.0]},
            title="Dates",
            x_is_date=True,
        )
        out = compact_line(spec, width=3)
        assert "2024-01-01" in out
        assert "2024-01-10" in out


class TestCompactBubble:
    def test_basic_matrix(self):
        """Basic presence/absence matrix renders correctly."""
        spec = BubbleSpec(
            y_labels=["Alice", "Bob"],
            col_names=["Age", "City"],
            matrix=[[True, False], [True, True]],
        )
        out = compact_bubble(spec, title="Test")
        assert "[COMPACT:bubble] Test" in out
        assert "cols: Age | City" in out
        assert "●" in out
        assert "·" in out
        lines = out.strip().split("\n")
        alice_line = [ln for ln in lines if "Alice" in ln][0]
        bob_line = [ln for ln in lines if "Bob" in ln][0]
        assert "|●·|" in alice_line
        assert "|●●|" in bob_line

    def test_empty_data(self):
        """Empty spec produces no-data message."""
        spec = BubbleSpec()
        out = compact_bubble(spec, title="Empty")
        assert "[COMPACT:bubble] Empty" in out
        assert "(no data)" in out

    def test_single_col(self):
        """Single column works."""
        spec = BubbleSpec(
            y_labels=["A"],
            col_names=["X"],
            matrix=[[True]],
        )
        out = compact_bubble(spec, title="Single")
        assert "cols: X" in out
        assert "|●|" in out

    def test_all_present(self):
        """All-present matrix uses only ● symbols."""
        spec = BubbleSpec(
            y_labels=["A"],
            col_names=["X", "Y", "Z"],
            matrix=[[True, True, True]],
        )
        out = compact_bubble(spec, title="Full")
        lines = out.strip().split("\n")
        a_line = [ln for ln in lines if ln.strip().startswith("A") and "|" in ln][0]
        assert "|●●●|" in a_line

    def test_all_absent(self):
        """All-absent matrix uses only · symbols."""
        spec = BubbleSpec(
            y_labels=["A"],
            col_names=["X", "Y"],
            matrix=[[False, False]],
        )
        out = compact_bubble(spec, title="Test")
        lines = out.strip().split("\n")
        a_line = [ln for ln in lines if ln.strip().startswith("A") and "|" in ln][0]
        assert "|··|" in a_line

    def test_label_alignment(self):
        """Labels are right-aligned to the longest label."""
        spec = BubbleSpec(
            y_labels=["Al", "Bobby"],
            col_names=["X"],
            matrix=[[True], [False]],
        )
        out = compact_bubble(spec, title="Align")
        lines = out.strip().split("\n")
        al_line = [ln for ln in lines if "Al" in ln and "|" in ln][0]
        bobby_line = [ln for ln in lines if "Bobby" in ln][0]
        # Al should be padded to match Bobby's width
        assert al_line.index("|") == bobby_line.index("|")

    def test_fill_rate_footer(self):
        """Compact bubble includes a fill-rate footer row."""
        spec = BubbleSpec(
            y_labels=["Alice", "Bob"],
            col_names=["Age", "City"],
            matrix=[[True, False], [True, True]],
            total_rows=2,
        )
        out = compact_bubble(spec, title="Test")
        assert "fill:" in out
        assert "Age:100%" in out
        assert "City:50%" in out


class TestCompactBubbleGrouped:
    def test_basic_grouped_output(self):
        """Grouped compact bubble shows percentages and counts."""
        from cplt.bubble import GroupedBubbleSpec
        from cplt.compact import compact_bubble_grouped

        spec = GroupedBubbleSpec(
            group_labels=["admin", "user"],
            col_names=["Cabin", "Age"],
            counts=[[1, 3], [0, 2]],
            group_sizes=[3, 2],
            total_rows=5,
        )
        out = compact_bubble_grouped(spec, title="Test")
        assert "[COMPACT:bubble] Test" in out
        assert "group:" in out
        assert "admin" in out
        assert "33%(1/3)" in out  # Cabin: 1/3
        assert "100%(3/3)" in out  # Age: 3/3
        assert "0%(0/2)" in out  # Cabin: 0/2
        assert "100%(2/2)" in out  # Age: 2/2

    def test_overall_fill_rate(self):
        """Grouped output includes overall fill-rate line."""
        from cplt.bubble import GroupedBubbleSpec
        from cplt.compact import compact_bubble_grouped

        spec = GroupedBubbleSpec(
            group_labels=["a", "b"],
            col_names=["X"],
            counts=[[2], [1]],
            group_sizes=[3, 2],
            total_rows=5,
        )
        out = compact_bubble_grouped(spec, title="Test")
        assert "overall:" in out
        assert "X:60%(3/5)" in out  # 2+1=3 out of 3+2=5


class TestCompactSummarise:
    def test_basic_output(self):
        """Basic summary table renders with header and columns."""
        summaries = [
            ColumnSummary(
                name="id",
                detected_type="numeric",
                row_count=100,
                non_null_count=100,
                unique_count=100,
                min_val="1.0",
                max_val="100.0",
                top_values=[("1", 1), ("2", 1), ("3", 1)],
            ),
            ColumnSummary(
                name="name",
                detected_type="text",
                row_count=100,
                non_null_count=95,
                unique_count=80,
                top_values=[("Alice", 5), ("Bob", 3)],
            ),
        ]
        out = compact_summarise(summaries, title="test.csv")
        assert "[COMPACT:summarise] test.csv" in out
        assert "rows: 100" in out
        assert "id" in out
        assert "numeric" in out
        assert "1.0" in out
        assert "100.0" in out
        assert "name" in out
        assert "text" in out
        assert "Alice(5)" in out

    def test_distribution_header(self):
        """Column header should say 'Distribution'."""
        summaries = [
            ColumnSummary(
                name="col",
                detected_type="text",
                row_count=10,
                non_null_count=10,
                unique_count=3,
                top_values=[("a", 5)],
            ),
        ]
        out = compact_summarise(summaries, title="t.csv")
        assert "Distribution" in out

    def test_empty_columns(self):
        """Empty summaries list produces no-data message."""
        out = compact_summarise([], title="empty.csv")
        assert "[COMPACT:summarise] empty.csv" in out
        assert "(no data)" in out

    def test_high_cardinality(self):
        """High cardinality columns show >10K unique."""
        summaries = [
            ColumnSummary(
                name="uid",
                detected_type="text",
                row_count=50000,
                non_null_count=50000,
                unique_count=50000,
                high_cardinality=True,
            ),
        ]
        out = compact_summarise(summaries, title="big.csv")
        assert ">10K unique" in out

    def test_sample_rows(self):
        """Sample rows are appended when provided."""
        summaries = [
            ColumnSummary(name="a", row_count=10, non_null_count=10, unique_count=5),
        ]
        sample = [{"a": "hello"}, {"a": "world"}]
        out = compact_summarise(summaries, title="s.csv", sample_rows=sample)
        assert "Sample" in out
        assert "hello" in out
        assert "world" in out

    def test_numeric_and_date_types(self):
        """Different detected types render correctly."""
        summaries = [
            ColumnSummary(
                name="price",
                detected_type="numeric",
                row_count=50,
                non_null_count=50,
                unique_count=30,
                min_val="1.5",
                max_val="99.9",
            ),
            ColumnSummary(
                name="created",
                detected_type="date",
                row_count=50,
                non_null_count=48,
                unique_count=40,
                min_val="2024-01-01",
                max_val="2024-12-31",
            ),
        ]
        out = compact_summarise(summaries, title="types.csv")
        assert "numeric" in out
        assert "date" in out
        assert "2024-01-01" in out

    def test_data_quality_section(self):
        """Data quality section appears with sentinel/whitespace/mixed info."""
        summaries = [
            ColumnSummary(
                name="amount",
                detected_type="numeric",
                row_count=10,
                non_null_count=8,
                unique_count=7,
                null_count=2,
                null_sentinel_count=1,
                zero_count=3,
                mean=42.5,
                stddev=12.3,
                whitespace_count=0,
            ),
            ColumnSummary(
                name="date",
                detected_type="date",
                row_count=10,
                non_null_count=10,
                unique_count=10,
                null_count=0,
                null_sentinel_count=0,
                date_formats=[("YYYY-MM-DD", 8), ("DD/MM/YYYY", 2)],
                whitespace_count=1,
            ),
            ColumnSummary(
                name="status",
                detected_type="text",
                row_count=10,
                non_null_count=10,
                unique_count=3,
                null_count=0,
                null_sentinel_count=2,
                mixed_type_pct="80% text, 20% numeric",
                mixed_type_examples=["123", "456"],
            ),
        ]
        out = compact_summarise(summaries, title="dq.csv")
        # Should have a Data Quality section
        assert "Data Quality" in out
        # Nulls column
        assert "Nulls" in out
        # Sentinels shown (>0 across columns)
        assert "Sentinels" in out
        # Zeros for numeric column
        assert "Zeros" in out
        # Mean/Stddev
        assert "42.500" in out
        assert "12.300" in out
        # Date formats
        assert "YYYY-MM-DD(8)" in out
        # Whitespace shown (>0 across columns)
        assert "Whitespace" in out
        # Mixed types
        assert "80% text" in out
        assert "123, 456" in out

    def test_data_quality_hides_zero_only_columns(self):
        """Sentinels/Whitespace columns hidden when all zeros."""
        summaries = [
            ColumnSummary(
                name="clean",
                detected_type="text",
                row_count=5,
                non_null_count=5,
                unique_count=5,
                null_count=0,
                null_sentinel_count=0,
                whitespace_count=0,
            ),
        ]
        out = compact_summarise(summaries, title="clean.csv")
        assert "Data Quality" in out
        assert "Sentinels" not in out
        assert "Whitespace" not in out


class TestCompactSummariseSmartDistribution:
    """Tests for smart Distribution column rendering in compact_summarise."""

    def test_distribution_header(self):
        """Column should be 'Distribution', not 'Top Values (freq)'."""
        summaries = [
            ColumnSummary(name="col", row_count=10, non_null_count=10, unique_count=3),
        ]
        out = compact_summarise(summaries, title="t.csv")
        assert "Distribution" in out
        assert "Top Values (freq)" not in out

    def test_id_column_shows_all_unique(self):
        """ID columns show '(all unique)' in Distribution."""
        summaries = [
            ColumnSummary(
                name="id",
                detected_type="numeric",
                row_count=100,
                non_null_count=100,
                unique_count=100,
                is_id=True,
            ),
        ]
        out = compact_summarise(summaries, title="t.csv")
        assert "(all unique)" in out

    def test_categorical_shows_percentages(self):
        """Categorical columns show value percentages."""
        summaries = [
            ColumnSummary(
                name="status",
                detected_type="text",
                row_count=10,
                non_null_count=10,
                unique_count=3,
                is_categorical=True,
                top_values=[("open", 5), ("closed", 3), ("pending", 2)],
            ),
        ]
        out = compact_summarise(summaries, title="t.csv")
        assert "open 50%" in out
        assert "closed 30%" in out
        assert "pending 20%" in out

    def test_categorical_with_other(self):
        """When there are >5 categories, the rest are lumped into 'other'."""
        top = [("a", 20), ("b", 15), ("c", 10), ("d", 8), ("e", 5)]
        summaries = [
            ColumnSummary(
                name="cat",
                detected_type="text",
                row_count=100,
                non_null_count=100,
                unique_count=10,
                is_categorical=True,
                top_values=top,
            ),
        ]
        out = compact_summarise(summaries, title="t.csv")
        assert "other 42%" in out

    def test_numeric_histogram_sparkline(self):
        """Numeric non-categorical columns show sparkline histogram."""
        bins = [2, 5, 10, 15, 20, 15, 10, 5, 2, 1]
        summaries = [
            ColumnSummary(
                name="age",
                detected_type="numeric",
                row_count=85,
                non_null_count=85,
                unique_count=50,
                min_val="1.0",
                max_val="100.0",
                histogram_bins=bins,
            ),
        ]
        out = compact_summarise(summaries, title="t.csv")
        # Should contain sparkline chars and range
        assert "1.0" in out
        assert "100.0" in out
        # Should contain at least one sparkline character
        spark_chars = set("▁▂▃▄▅▆▇█")
        dist_has_spark = any(c in spark_chars for c in out)
        assert dist_has_spark

    def test_null_count_instead_of_non_null(self):
        """Table shows 'Nulls' column, not 'Non-null'."""
        summaries = [
            ColumnSummary(
                name="col",
                row_count=10,
                non_null_count=8,
                null_count=2,
                unique_count=5,
            ),
        ]
        out = compact_summarise(summaries, title="t.csv")
        assert "Nulls" in out
        assert "Non-null" not in out

    def test_no_rows_column(self):
        """The Rows column is dropped (already shown in header)."""
        summaries = [
            ColumnSummary(name="col", row_count=10, non_null_count=10, unique_count=5),
        ]
        out = compact_summarise(summaries, title="t.csv")
        lines = out.split("\n")
        # The header line should not have "Rows" as a column
        header_line = [l for l in lines if "Column" in l and "Type" in l]
        assert header_line
        assert "Rows" not in header_line[0]
