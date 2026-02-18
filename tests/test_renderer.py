"""Tests for timeline rendering behavior."""

from __future__ import annotations

import re
from datetime import datetime

import csvplot.renderer as renderer
from csvplot.models import BarSpec, LineSpec, PlotSpec, Segment
from csvplot.renderer import render, render_bar, render_line


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


def test_two_layer_timeline_has_correct_y_tick_count() -> None:
    spec = PlotSpec(
        segments=[
            Segment(
                row_index=1,
                layer=0,
                y_label="row-a",
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 2),
            ),
            Segment(
                row_index=1,
                layer=1,
                y_label="row-a",
                start=datetime(2024, 1, 2),
                end=datetime(2024, 1, 3),
            ),
            Segment(
                row_index=2,
                layer=0,
                y_label="row-b",
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 2),
            ),
            Segment(
                row_index=2,
                layer=1,
                y_label="row-b",
                start=datetime(2024, 1, 2),
                end=datetime(2024, 1, 3),
            ),
            Segment(
                row_index=3,
                layer=0,
                y_label="row-c",
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 2),
            ),
            Segment(
                row_index=3,
                layer=1,
                y_label="row-c",
                start=datetime(2024, 1, 2),
                end=datetime(2024, 1, 3),
            ),
        ],
        title="tick-count",
        x_pair_names=[("start_1", "end_1"), ("start_2", "end_2")],
    )

    output = render(spec, build=True)
    assert output is not None

    clean = re.sub(r"\x1b\[[0-9;]*m", "", output)
    tick_labels = re.findall(r"(?m)^(row-[abc])┤", clean)
    assert len(tick_labels) == 3


def test_render_bar_integer_ticks_use_integer_labels(monkeypatch) -> None:
    recorded: dict[str, tuple[list[int], list[str]]] = {}

    def _fake_yticks(ticks, labels):
        recorded["y"] = (list(ticks), list(labels))

    monkeypatch.setattr(renderer.plt, "yticks", _fake_yticks)
    spec = BarSpec(labels=["A", "B"], values=[577.0, 216.0], title="bar-int")

    out = render_bar(spec, build=True)
    assert out is not None
    assert "y" in recorded
    _, labels = recorded["y"]
    assert labels
    assert all("." not in label for label in labels)


def test_render_bar_with_labels_calls_text_for_each_bar(monkeypatch) -> None:
    calls: list[tuple[str, object, object, str]] = []

    def _fake_text(text, *, x, y, color):
        calls.append((text, x, y, color))

    monkeypatch.setattr(renderer.plt, "text", _fake_text)
    spec = BarSpec(labels=["A", "B"], values=[3.0, 1.0], title="bar-labels", show_labels=True)

    out = render_bar(spec, build=True)
    assert out is not None
    assert len(calls) == 2
    assert calls[0][0] == "3"
    assert calls[1][0] == "1"


def test_render_line_only_labels_multi_series(monkeypatch) -> None:
    labels: list[str | None] = []
    original_plot = renderer.plt.plot

    def _capture_plot(*args, **kwargs):
        labels.append(kwargs.get("label"))
        return original_plot(*args, **kwargs)

    monkeypatch.setattr(renderer.plt, "plot", _capture_plot)
    spec = LineSpec(
        x_values=["a", "b"],
        y_series={"s1": [1.0, 2.0], "s2": [2.0, 1.0]},
        title="line-legend",
    )

    out = render_line(spec, build=True)
    assert out is not None
    assert labels == ["s1", "s2"]


def test_render_line_suppresses_single_series_legend_label(monkeypatch) -> None:
    labels: list[str | None] = []
    original_plot = renderer.plt.plot

    def _capture_plot(*args, **kwargs):
        labels.append(kwargs.get("label"))
        return original_plot(*args, **kwargs)

    monkeypatch.setattr(renderer.plt, "plot", _capture_plot)
    spec = LineSpec(x_values=["a", "b"], y_series={"s1": [1.0, 2.0]}, title="line-single")

    out = render_line(spec, build=True)
    assert out is not None
    assert labels == [None]
