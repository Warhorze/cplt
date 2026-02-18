"""Tests for timeline rendering behavior."""

from __future__ import annotations

from datetime import datetime

from csvplot.models import PlotSpec, Segment
from csvplot.renderer import render


def test_render_includes_all_unique_txt_labels_per_sub_row() -> None:
    spec = PlotSpec(
        segments=[
            Segment(
                row_index=1,
                layer=0,
                y_label="group-a",
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 2),
                txt_label="120290146",
            ),
            Segment(
                row_index=1,
                layer=1,
                y_label="group-a",
                start=datetime(2024, 1, 3),
                end=datetime(2024, 1, 4),
                txt_label="117987179",
            ),
            Segment(
                row_index=2,
                layer=0,
                y_label="group-a",
                start=datetime(2024, 1, 5),
                end=datetime(2024, 1, 6),
                txt_label="333333333",
            ),
        ],
        title="txt-test",
        x_pair_names=[("start_1", "end_1"), ("start_2", "end_2")],
    )

    output = render(spec, build=True)
    assert output is not None
    assert "group-a | 120290146, 117987179" in output


def test_render_legend_includes_layer_marker_style() -> None:
    spec = PlotSpec(
        segments=[
            Segment(
                row_index=1,
                layer=0,
                y_label="group-a",
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 2),
                color_key="alpha",
            ),
            Segment(
                row_index=1,
                layer=1,
                y_label="group-a",
                start=datetime(2024, 1, 2),
                end=datetime(2024, 1, 3),
                color_key="beta",
            ),
        ],
        title="legend-test",
        x_pair_names=[("start_1", "end_1"), ("start_2", "end_2")],
        color_col_name="status",
    )

    output = render(spec, build=True)
    assert output is not None
    assert "Legend" in output
    assert "marker=hd" in output
    assert "marker=sd" in output
