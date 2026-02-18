"""Core data structures for csvplot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Segment:
    row_index: int
    layer: int
    y_label: str
    start: datetime
    end: datetime
    color_key: str | None = None
    txt_label: str = ""


@dataclass(frozen=True, slots=True)
class VLine:
    date: datetime
    label: str = ""


@dataclass
class BarSpec:
    labels: list[str] = field(default_factory=list)
    values: list[float] = field(default_factory=list)
    title: str = "csvplot"
    horizontal: bool = False
    show_labels: bool = False


@dataclass
class LineSpec:
    x_values: list[str] = field(default_factory=list)
    y_series: dict[str, list[float]] = field(default_factory=dict)
    title: str = "csvplot"
    x_is_date: bool = False


@dataclass
class PlotSpec:
    segments: list[Segment] = field(default_factory=list)
    vlines: list[VLine] = field(default_factory=list)
    view_start: datetime | None = None
    view_end: datetime | None = None
    title: str = "csvplot"
    x_pair_names: list[tuple[str, str]] = field(default_factory=list)
    color_col_name: str | None = None
