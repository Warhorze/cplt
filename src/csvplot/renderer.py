"""Render a PlotSpec to the terminal using plotext."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

import plotext as plt
from rich import print as rprint

from csvplot.models import BarSpec, LineSpec, PlotSpec, Segment

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
_Y_GROUP_GAP = 1.2


def _build_color_map(segments: list[Segment]) -> dict[str, str]:
    """Assign a color to each unique color_key, or auto-color by y_label if no color_key."""
    has_color_keys = any(seg.color_key for seg in segments)
    if has_color_keys:
        keys: list[str] = []
        seen: set[str] = set()
        for seg in segments:
            if seg.color_key and seg.color_key not in seen:
                keys.append(seg.color_key)
                seen.add(seg.color_key)
        return {key: PALETTE[i % len(PALETTE)] for i, key in enumerate(keys)}
    else:
        # Auto-color by y_label
        labels: list[str] = []
        seen_labels: set[str] = set()
        for seg in segments:
            if seg.y_label not in seen_labels:
                labels.append(seg.y_label)
                seen_labels.add(seg.y_label)
        return {label: PALETTE[i % len(PALETTE)] for i, label in enumerate(labels)}


def _dt_to_str(dt: datetime) -> str:
    """Convert datetime to plotext-compatible date string."""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _date_form_for_range(start: datetime, end: datetime) -> str:
    """Pick an x-axis date label format based on visible timespan."""
    span_seconds = abs((end - start).total_seconds())
    if span_seconds >= 365 * 24 * 3600:
        return "Y-m"
    if span_seconds >= 2 * 24 * 3600:
        return "Y-m-d"
    if span_seconds >= 6 * 3600:
        return "m-d H:M"
    if span_seconds >= 3600:
        return "H:M"
    return "H:M:S"


def _assign_sub_rows(segments: list[Segment]) -> dict[Segment, int]:
    """Assign sub-rows by row identity: each CSV row gets its own line."""
    groups: dict[str, list[Segment]] = defaultdict(list)
    for seg in segments:
        groups[seg.y_label].append(seg)

    sub_row_map: dict[Segment, int] = {}
    for group_segments in groups.values():
        # Collect unique row_index values preserving first-seen order
        seen: dict[int, int] = {}
        for seg in group_segments:
            if seg.row_index not in seen:
                seen[seg.row_index] = len(seen)
        for seg in group_segments:
            sub_row_map[seg] = seen[seg.row_index]
    return sub_row_map


def render(spec: PlotSpec, build: bool = False) -> str | None:
    """Render a PlotSpec to the terminal, or return canvas string if build=True."""
    plt.clear_figure()
    plt.date_form("Y-m-d H:M:S", "Y-m-d H:M:S")
    plt.theme("clear")
    if spec.segments:
        data_start = min(seg.start for seg in spec.segments)
        data_end = max(seg.end for seg in spec.segments)
        view_start = spec.view_start or data_start
        view_end = spec.view_end or data_end
        plt.date_form("Y-m-d H:M:S", _date_form_for_range(view_start, view_end))

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

    # Collect txt labels per (y_label, sub_row) for y-axis display
    has_txt = any(seg.txt_label for seg in spec.segments)
    txt_by_sub_row: dict[tuple[str, int], str] = {}
    if has_txt:
        for seg in spec.segments:
            key = (seg.y_label, sub_row_map[seg])
            if key not in txt_by_sub_row and seg.txt_label:
                txt_by_sub_row[key] = seg.txt_label

    y_base: dict[str, float] = {}
    y_ticks: list[float] = []
    y_tick_labels: list[str] = []
    cursor = 0.0
    max_y = 0.0
    for label in y_labels:
        label_segments = segments_by_label[label]
        max_sub_row = max(sub_row_map[s] for s in label_segments) if label_segments else 0
        max_layer = max(s.layer for s in label_segments) if label_segments else 0
        group_min = cursor
        group_max = cursor + max_sub_row * _SUB_ROW_HEIGHT + max_layer * _LAYER_OFFSET
        y_base[label] = cursor

        if has_txt and max_sub_row > 0:
            # One tick per sub-row showing y_label + txt value
            for sr in range(max_sub_row + 1):
                tick_y = cursor + sr * _SUB_ROW_HEIGHT
                txt = txt_by_sub_row.get((label, sr), "")
                tick_label = f"{label} | {txt}" if txt else label
                y_ticks.append(tick_y)
                y_tick_labels.append(tick_label)
        else:
            y_ticks.append((group_min + group_max) / 2)
            y_tick_labels.append(label)

        max_y = max(max_y, group_max)
        cursor = group_max + _Y_GROUP_GAP

    # Scale figure height from computed vertical span.
    plot_height = max(12, int((max_y + _Y_GROUP_GAP) * 2.0) + 8)
    plt.plotsize(None, plot_height)

    has_color_keys = any(seg.color_key for seg in spec.segments)

    legend_layer_order: list[str] = []
    legend_values_by_layer: dict[str, list[str]] = {}
    legend_value_seen: dict[str, set[str]] = {}

    # Build layer display names from x_pair_names
    def _layer_display(layer: int) -> str:
        if spec.x_pair_names and layer < len(spec.x_pair_names):
            s, e = spec.x_pair_names[layer]
            return f"{s} \u2013 {e}"
        return f"layer {layer}" if layer > 0 else "primary"

    def _resolve_color(seg: Segment, default: str) -> str:
        if has_color_keys:
            if seg.color_key is None:
                return default
            return color_map.get(seg.color_key, default)
        return color_map.get(seg.y_label, default)

    def _add_legend(layer_name: str, color_key: str | None) -> None:
        if layer_name not in legend_values_by_layer:
            legend_layer_order.append(layer_name)
            legend_values_by_layer[layer_name] = []
            legend_value_seen[layer_name] = set()
        if color_key:
            seen_values = legend_value_seen[layer_name]
            if color_key not in seen_values:
                legend_values_by_layer[layer_name].append(color_key)
                seen_values.add(color_key)

    # Layer marker styles: visually distinct per layer
    _LAYER_MARKERS = ["hd", "braille", "dot", "sd"]

    # Plot non-primary layers first (behind primary)
    for seg in spec.segments:
        if seg.layer == 0:
            continue
        y = y_base[seg.y_label] + sub_row_map[seg] * _SUB_ROW_HEIGHT + seg.layer * _LAYER_OFFSET
        color = _resolve_color(seg, "gray")
        layer_name = _layer_display(seg.layer)
        _add_legend(layer_name, seg.color_key)
        marker_style = _LAYER_MARKERS[seg.layer % len(_LAYER_MARKERS)]
        plt.plot(
            [_dt_to_str(seg.start), _dt_to_str(seg.end)],
            [y, y],
            marker=marker_style,
            color=color,
            label=None,
        )

    # Plot primary segments (layer 0) on top
    for seg in spec.segments:
        if seg.layer != 0:
            continue
        y = y_base[seg.y_label] + sub_row_map[seg] * _SUB_ROW_HEIGHT
        color = _resolve_color(seg, "white")
        layer_name = _layer_display(0)
        _add_legend(layer_name, seg.color_key)
        plt.plot(
            [_dt_to_str(seg.start), _dt_to_str(seg.end)],
            [y, y],
            marker="hd",
            color=color,
            label=None,
        )

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
    plt.yticks(y_ticks, y_tick_labels)
    plt.xlabel("Date")
    plt.title(spec.title)

    # Apply view window if specified
    if spec.view_start:
        plt.xlim(left=_dt_to_str(spec.view_start))
    if spec.view_end:
        plt.xlim(right=_dt_to_str(spec.view_end))

    legend_entries: list[str] = []
    for layer_name in legend_layer_order:
        layer_values = legend_values_by_layer[layer_name]
        if layer_values and spec.color_col_name:
            values = ", ".join(layer_values)
            legend_entries.append(f"{layer_name} ({spec.color_col_name}: {values})")
        elif layer_values:
            values = ", ".join(layer_values)
            legend_entries.append(f"{layer_name} ({values})")
        else:
            legend_entries.append(layer_name)

    if build:
        canvas = plt.build()
        if legend_entries:
            canvas += "\n\nLegend"
            for label in legend_entries:
                canvas += f"\n- {label}"
        return canvas

    plt.show()
    if legend_entries:
        rprint("\nLegend")
        for label in legend_entries:
            rprint(f"- {label}")
    return None


def render_bar(spec: BarSpec, build: bool = False) -> str | None:
    """Render a BarSpec as a bar chart."""
    plt.clear_figure()
    plt.theme("clear")

    # Use a single bar color for cleaner magnitude comparison in categorical distributions.
    colors = ["yellow"] * max(1, len(spec.labels))

    orientation = "horizontal" if spec.horizontal else "vertical"
    plt.bar(spec.labels, spec.values, color=colors, orientation=orientation)

    plt.title(spec.title)

    if build:
        return plt.build()

    plt.show()
    return None


def render_line(spec: LineSpec, build: bool = False) -> str | None:
    """Render a LineSpec as a line chart."""
    plt.clear_figure()
    plt.date_form("Y-m-d H:M:S", "Y-m-d H:M:S")
    plt.theme("clear")

    # Normalize date strings to plotext's expected format (Y-m-d H:M:S)
    x_display = spec.x_values
    if spec.x_is_date:
        from csvplot.reader import parse_datetime as _pd

        normalized: list[str] = []
        parsed_dates: list[datetime] = []
        for value in spec.x_values:
            parsed = _pd(value)
            normalized.append(_dt_to_str(parsed) if parsed else value)
            if parsed:
                parsed_dates.append(parsed)
        x_display = normalized
        if parsed_dates:
            plt.date_form(
                "Y-m-d H:M:S",
                _date_form_for_range(parsed_dates[0], parsed_dates[-1]),
            )

    for i, (series_name, y_vals) in enumerate(spec.y_series.items()):
        color = PALETTE[i % len(PALETTE)]
        if spec.x_is_date:
            plt.plot(x_display, y_vals, marker="braille", color=color, label=series_name)
        else:
            plt.plot(
                list(range(len(y_vals))),
                y_vals,
                marker="braille",
                color=color,
                label=series_name,
            )
            plt.xticks(list(range(len(spec.x_values))), spec.x_values)

    plt.title(spec.title)

    if build:
        return plt.build()

    plt.show()
    return None
