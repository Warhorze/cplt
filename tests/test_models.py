"""Tests for csvplot.models."""

from __future__ import annotations

from datetime import datetime

from csvplot.models import BarSpec, LineSpec, Marker, PlotSpec, Segment


class TestSegment:
    def test_creation(self) -> None:
        seg = Segment(
            row_index=1,
            layer=0,
            y_label="task1",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 10),
            color_key="red",
        )
        assert seg.row_index == 1
        assert seg.layer == 0
        assert seg.y_label == "task1"
        assert seg.color_key == "red"

    def test_frozen(self) -> None:
        seg = Segment(
            row_index=1,
            layer=0,
            y_label="task1",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 10),
        )
        import pytest

        with pytest.raises(AttributeError):
            seg.y_label = "changed"  # type: ignore[misc]

    def test_default_color_key(self) -> None:
        seg = Segment(
            row_index=1,
            layer=1,
            y_label="task1",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 10),
        )
        assert seg.color_key == ""

    def test_layer_supports_arbitrary_int(self) -> None:
        seg = Segment(
            row_index=1,
            layer=3,
            y_label="task1",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 10),
        )
        assert seg.layer == 3


class TestPlotSpec:
    def test_defaults(self) -> None:
        spec = PlotSpec()
        assert spec.segments == []
        assert spec.markers == []
        assert spec.view_start is None
        assert spec.view_end is None

    def test_with_data(self) -> None:
        seg = Segment(
            row_index=1,
            layer=0,
            y_label="A",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 2, 1),
        )
        marker = Marker(date=datetime(2024, 1, 15), label="midpoint")
        spec = PlotSpec(segments=[seg], markers=[marker])
        assert len(spec.segments) == 1
        assert len(spec.markers) == 1
        assert spec.markers[0].label == "midpoint"


class TestBarSpec:
    def test_defaults(self) -> None:
        spec = BarSpec()
        assert spec.labels == []
        assert spec.values == []
        assert spec.title == "csvplot"
        assert spec.horizontal is False

    def test_with_data(self) -> None:
        spec = BarSpec(
            labels=["A", "B", "C"],
            values=[10.0, 20.0, 30.0],
            title="test",
            horizontal=True,
        )
        assert len(spec.labels) == 3
        assert spec.values[1] == 20.0
        assert spec.horizontal is True


class TestLineSpec:
    def test_defaults(self) -> None:
        spec = LineSpec()
        assert spec.x_values == []
        assert spec.y_series == {}
        assert spec.title == "csvplot"
        assert spec.x_is_date is False

    def test_with_data(self) -> None:
        spec = LineSpec(
            x_values=["2024-01-01", "2024-01-02"],
            y_series={"temp": [10.0, 11.0], "humidity": [60.0, 62.0]},
            title="weather",
            x_is_date=True,
        )
        assert len(spec.x_values) == 2
        assert len(spec.y_series) == 2
        assert spec.x_is_date is True
