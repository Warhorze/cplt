"""Core data structures for cplt."""

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


@dataclass(frozen=True, slots=True)
class Dot:
    row_index: int
    layer: int
    y_label: str
    date: datetime
    color_key: str | None = None


@dataclass
class BarSpec:
    labels: list[str] = field(default_factory=list)
    values: list[float] = field(default_factory=list)
    title: str = "cplt"
    horizontal: bool = False
    show_labels: bool = False


@dataclass
class LineSpec:
    x_values: list[str] = field(default_factory=list)
    y_series: dict[str, list[float]] = field(default_factory=dict)
    title: str = "cplt"
    x_is_date: bool = False


@dataclass
class HistSpec:
    bin_edges: list[float] = field(default_factory=list)
    bin_counts: list[int] = field(default_factory=list)
    total_count: int = 0
    null_count: int = 0
    mean: float = 0.0
    median: float = 0.0
    stddev: float = 0.0
    title: str = "cplt"
    column: str = ""


@dataclass
class PlotSpec:
    segments: list[Segment] = field(default_factory=list)
    vlines: list[VLine] = field(default_factory=list)
    view_start: datetime | None = None
    view_end: datetime | None = None
    title: str = "cplt"
    x_pair_names: list[tuple[str, str]] = field(default_factory=list)
    color_col_name: str | None = None
    dots: list[Dot] = field(default_factory=list)
    dot_col_names: list[str] = field(default_factory=list)
