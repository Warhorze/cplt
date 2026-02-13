"""Render a PlotSpec to the terminal using plotext."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

import plotext as plt
from rich import print as rprint

from csvplot.models import PlotSpec, Segment

# Rainbow-style color palette: base + bright variants for maximum variety
PALETTE = [
    "red",
    "orange",
    "yellow",
    "green",
    "cyan",
    "blue",
    "violet",
    "magenta",
    "red+",
    "orange+",
    "yellow+",
    "green+",
    "cyan+",
    "blue+",
    "violet+",
    "magenta+",
]

# Vertical spacing inside a y-label group.
_SUB_ROW_HEIGHT = 1.0
_LAYER_OFFSET = 0.45
_LABEL_Y_OFFSETS = (0.20, 0.35)
_LABEL_TRUNCATE = 15
_Y_GROUP_GAP = 1.2


def _build_color_map(segments: list[Segment]) -> dict[str, str]:
    """Assign a color to each unique color_key."""
    keys: list[str] = []
    seen: set[str] = set()
    for seg in segments:
        if seg.color_key and seg.color_key not in seen:
            keys.append(seg.color_key)
            seen.add(seg.color_key)
    return {key: PALETTE[i % len(PALETTE)] for i, key in enumerate(keys)}


def _dt_to_str(dt: datetime) -> str:
    """Convert datetime to plotext-compatible date string."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _midpoint(start: datetime, end: datetime) -> datetime:
    """Return the midpoint between two datetimes."""
    return start + (end - start) / 2


def _assign_sub_rows(segments: list[Segment]) -> dict[Segment, int]:
    """Assign sub-rows per (y_label, layer) using greedy interval packing."""
    groups: dict[tuple[str, int], list[Segment]] = defaultdict(list)
    for seg in segments:
        groups[(seg.y_label, seg.layer)].append(seg)

    sub_row_map: dict[Segment, int] = {}
    for group_segments in groups.values():
        group_segments.sort(key=lambda s: (s.start, s.end))
        row_ends: list[datetime] = []
        for seg in group_segments:
            assigned = False
            for idx, row_end in enumerate(row_ends):
                if seg.start >= row_end:
                    sub_row_map[seg] = idx
                    row_ends[idx] = seg.end
                    assigned = True
                    break
            if not assigned:
                sub_row_map[seg] = len(row_ends)
                row_ends.append(seg.end)
    return sub_row_map


def _truncate_label(label: str) -> str:
    if len(label) <= _LABEL_TRUNCATE:
        return label
    return f"{label[:_LABEL_TRUNCATE]}..."


def _layout_text_labels(
    labels: list[tuple[str, datetime, float, str]],
    *,
    x_min: datetime,
    x_max: datetime,
) -> list[tuple[str, str, float, str]]:
    """Apply a basic collision-avoidance strategy for segment labels."""
    if not labels:
        return []

    x_span = max((x_max - x_min).total_seconds(), 1.0)
    min_x_distance = x_span * 0.05

    sorted_labels = sorted(labels, key=lambda item: item[1])
    placed: list[tuple[str, datetime, float, str]] = []
    last_state_by_band: dict[int, tuple[datetime, int]] = {}

    for raw_text, x_dt, y_base, color in sorted_labels:
        band = int(round(y_base * 10))
        offset_index = 0
        previous_state = last_state_by_band.get(band)
        if previous_state is not None:
            prev_x, prev_offset_index = previous_state
            if abs((x_dt - prev_x).total_seconds()) <= min_x_distance:
                offset_index = 1 - prev_offset_index

        y = y_base + _LABEL_Y_OFFSETS[offset_index]
        overlaps = any(
            abs(y - existing_y) < 1e-8
            and abs((x_dt - existing_x).total_seconds()) <= min_x_distance
            for _, existing_x, existing_y, _ in placed
        )
        if overlaps:
            continue

        placed.append((_truncate_label(raw_text), x_dt, y, color))
        last_state_by_band[band] = (x_dt, offset_index)

    return [(text, _dt_to_str(x_dt), y, color) for text, x_dt, y, color in placed]


def render(spec: PlotSpec) -> None:
    """Render a PlotSpec to the terminal."""
    plt.clear_figure()
    plt.date_form("Y-m-d H:M:S")
    plt.theme("clear")

    # Collect unique y-labels preserving order
    y_labels: list[str] = []
    seen: set[str] = set()
    for seg in spec.segments:
        if seg.y_label not in seen:
            y_labels.append(seg.y_label)
            seen.add(seg.y_label)

    sub_row_map = _assign_sub_rows(spec.segments)
    color_map = _build_color_map(spec.segments)

    segments_by_label: dict[str, list[Segment]] = defaultdict(list)
    for seg in spec.segments:
        segments_by_label[seg.y_label].append(seg)

    y_base: dict[str, float] = {}
    y_ticks: list[float] = []
    cursor = 0.0
    max_y = 0.0
    for label in y_labels:
        label_segments = segments_by_label[label]
        max_sub_row = max(sub_row_map[s] for s in label_segments) if label_segments else 0
        max_layer = max(s.layer for s in label_segments) if label_segments else 0
        group_min = cursor
        group_max = cursor + max_sub_row * _SUB_ROW_HEIGHT + max_layer * _LAYER_OFFSET
        y_base[label] = cursor
        y_ticks.append((group_min + group_max) / 2)
        max_y = max(max_y, group_max)
        cursor = group_max + _Y_GROUP_GAP

    # Scale figure height from computed vertical span.
    plot_height = max(12, int((max_y + _Y_GROUP_GAP) * 2.0) + 8)
    plt.plotsize(None, plot_height)

    # Collect text labels to render after all segments
    text_labels: list[tuple[str, datetime, float, str]] = []  # (label, x_dt, y, color)
    legend_seen: set[tuple[str, str]] = set()
    legend_entries: list[str] = []

    # Plot non-primary layers first (behind primary)
    for seg in spec.segments:
        if seg.layer == 0:
            continue
        y = y_base[seg.y_label] + sub_row_map[seg] * _SUB_ROW_HEIGHT + seg.layer * _LAYER_OFFSET
        color = color_map.get(seg.color_key, "gray")
        layer_name = f"layer {seg.layer}"
        legend_key = (layer_name, seg.color_key)
        legend_label = f"{layer_name} ({seg.color_key})" if seg.color_key else layer_name
        if legend_key not in legend_seen:
            legend_entries.append(legend_label)
        plt.plot(
            [_dt_to_str(seg.start), _dt_to_str(seg.end)],
            [y, y],
            marker="dot",
            color=color,
            label=None,
        )
        legend_seen.add(legend_key)
        if seg.txt_label:
            mid = _midpoint(seg.start, seg.end)
            text_labels.append((seg.txt_label, mid, y, color))

    # Plot primary segments (layer 0) on top
    for seg in spec.segments:
        if seg.layer != 0:
            continue
        y = y_base[seg.y_label] + sub_row_map[seg] * _SUB_ROW_HEIGHT
        color = color_map.get(seg.color_key, "white")
        legend_key = ("primary", seg.color_key)
        legend_label = f"primary ({seg.color_key})" if seg.color_key else "primary"
        if legend_key not in legend_seen:
            legend_entries.append(legend_label)
        plt.plot(
            [_dt_to_str(seg.start), _dt_to_str(seg.end)],
            [y, y],
            marker="dot",
            color=color,
            label=None,
        )
        legend_seen.add(legend_key)
        if seg.txt_label:
            mid = _midpoint(seg.start, seg.end)
            text_labels.append((seg.txt_label, mid, y, color))

    # Render text labels at segment midpoints
    x_min = min((s.start for s in spec.segments), default=datetime.now())
    x_max = max((s.end for s in spec.segments), default=x_min + timedelta(seconds=1))
    for label, x_str, y, color in _layout_text_labels(text_labels, x_min=x_min, x_max=x_max):
        plt.text(label, x=x_str, y=y, color=color)

    # Plot markers as vertical lines
    for marker in spec.markers:
        dt_str = _dt_to_str(marker.date)
        plt.vline(dt_str, color="red+")
        if marker.label:
            plt.text(
                marker.label,
                x=dt_str,
                y=max_y + 0.3,
                color="red+",
            )

    # Configure axes
    plt.yticks(y_ticks, y_labels)
    plt.xlabel("Date")
    plt.title("csvplot")

    # Apply view window if specified
    if spec.view_start:
        plt.xlim(left=_dt_to_str(spec.view_start))
    if spec.view_end:
        plt.xlim(right=_dt_to_str(spec.view_end))

    plt.show()
    if legend_entries:
        rprint("\nLegend")
        for label in legend_entries:
            rprint(f"- {label}")
