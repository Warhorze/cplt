"""Core data structures for csvplot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Segment:
    layer: int
    y_label: str
    start: datetime
    end: datetime
    color_key: str = ""
    txt_label: str = ""


@dataclass(frozen=True, slots=True)
class Marker:
    date: datetime
    label: str = ""


@dataclass
class PlotSpec:
    segments: list[Segment] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)
    view_start: datetime | None = None
    view_end: datetime | None = None
