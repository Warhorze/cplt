"""Compact token-efficient plot output for LLM consumption."""

from __future__ import annotations

from collections import defaultdict

from csvplot.bubble import BubbleSpec
from csvplot.models import BarSpec, LineSpec, PlotSpec, Segment
from csvplot.summarise import ColumnSummary


def rle_encode(chars: list[str]) -> str:
    """Run-length encode a list of single characters.

    Character followed by integer = repeat: █3 = 3 filled cells.
    Count of 1 is omitted: █ = single filled cell.
    """
    if not chars:
        return ""
    result: list[str] = []
    current = chars[0]
    count = 1
    for ch in chars[1:]:
        if ch == current:
            count += 1
        else:
            result.append(current if count == 1 else f"{current}{count}")
            current = ch
            count = 1
    result.append(current if count == 1 else f"{current}{count}")
    return "".join(result)


# Layer characters: layer 0 = █, layer 1 = #, layer 2+ = =
_LAYER_CHARS = ["█", "#", "="]


def _layer_char(layer: int) -> str:
    if layer < len(_LAYER_CHARS):
        return _LAYER_CHARS[layer]
    return _LAYER_CHARS[-1]


def _assign_sub_rows(segments: list[Segment]) -> dict[int, dict[int, int]]:
    """Return {y_label_index: {row_index: sub_row}} mapping."""
    groups: dict[str, list[Segment]] = defaultdict(list)
    for seg in segments:
        groups[seg.y_label].append(seg)

    result: dict[int, dict[int, int]] = {}
    label_to_idx: dict[str, int] = {}
    for seg in segments:
        if seg.y_label not in label_to_idx:
            label_to_idx[seg.y_label] = len(label_to_idx)

    for label, segs in groups.items():
        seen: dict[int, int] = {}
        for seg in segs:
            if seg.row_index not in seen:
                seen[seg.row_index] = len(seen)
        result[label_to_idx[label]] = seen

    return result


def compact_timeline(spec: PlotSpec, width: int = 60) -> str:
    """Render a PlotSpec as compact RLE-encoded ASCII."""
    lines: list[str] = []
    lines.append(f"[COMPACT:timeline] {spec.title}")

    if not spec.segments:
        lines.append("---")
        lines.append("(no data)")
        lines.append("---")
        return "\n".join(lines)

    # Compute time range
    all_starts = [s.start for s in spec.segments]
    all_ends = [s.end for s in spec.segments]
    t_min = spec.view_start or min(all_starts)
    t_max = spec.view_end or max(all_ends)
    t_range = (t_max - t_min).total_seconds()

    lines.append(f"x: {t_min.strftime('%Y-%m-%d')} .. {t_max.strftime('%Y-%m-%d')} | w={width}")
    lines.append("---")

    # Collect unique y-labels preserving order
    y_labels: list[str] = []
    seen: set[str] = set()
    for seg in spec.segments:
        if seg.y_label not in seen:
            y_labels.append(seg.y_label)
            seen.add(seg.y_label)

    # Group segments by y_label
    segments_by_label: dict[str, list[Segment]] = defaultdict(list)
    for seg in spec.segments:
        segments_by_label[seg.y_label].append(seg)

    # Sub-row assignment
    sub_rows: dict[str, dict[int, int]] = {}
    for label, segs in segments_by_label.items():
        row_seen: dict[int, int] = {}
        for seg in segs:
            if seg.row_index not in row_seen:
                row_seen[seg.row_index] = len(row_seen)
        sub_rows[label] = row_seen

    # Find max label width for alignment
    max_label_width = max(len(lb) for lb in y_labels)

    # Compute max layer count across all segments
    max_layer = max(s.layer for s in spec.segments)

    def _map_pos(dt_val) -> int:
        if t_range == 0:
            return 0
        frac = (dt_val - t_min).total_seconds() / t_range
        return max(0, min(width - 1, int(frac * (width - 1) + 0.5)))

    for label in y_labels:
        segs = segments_by_label[label]
        max_sub = max(sub_rows[label].values()) if sub_rows[label] else 0

        # For each layer, for each sub-row, produce a row
        for layer in range(max_layer + 1):
            layer_segs = [s for s in segs if s.layer == layer]
            if not layer_segs:
                continue
            for sub_idx in range(max_sub + 1):
                matching = [s for s in layer_segs if sub_rows[label][s.row_index] == sub_idx]
                if not matching:
                    continue

                row_chars = ["·"] * width
                char = _layer_char(layer)
                for seg in matching:
                    start_pos = _map_pos(seg.start)
                    end_pos = _map_pos(seg.end)
                    for i in range(start_pos, end_pos + 1):
                        row_chars[i] = char

                padded = label.ljust(max_label_width)
                lines.append(f"{padded}  |{rle_encode(row_chars)}|")

    lines.append("---")

    # Vertical reference lines
    if spec.vlines:
        vline_strs = []
        for vl in spec.vlines:
            s = vl.date.strftime("%Y-%m-%d")
            if vl.label:
                s += f' "{vl.label}"'
            vline_strs.append(s)
        lines.append("vlines: " + ", ".join(vline_strs))

    # Legend (color keys)
    if spec.color_col_name:
        color_keys: list[str] = []
        seen_keys: set[str] = set()
        for seg in spec.segments:
            if seg.color_key and seg.color_key not in seen_keys:
                color_keys.append(seg.color_key)
                seen_keys.add(seg.color_key)
        if color_keys:
            legend_parts = ", ".join(f"{k}={_layer_char(0)}" for k in color_keys)
            lines.append(f"legend: {spec.color_col_name}: {legend_parts}")

    return "\n".join(lines)


def compact_bar(spec: BarSpec, width: int = 40) -> str:
    """Render a BarSpec as compact RLE-encoded ASCII."""
    lines: list[str] = []
    lines.append(f"[COMPACT:bar] {spec.title}")
    lines.append("---")

    if not spec.labels:
        lines.append("(no data)")
        lines.append("---")
        return "\n".join(lines)

    max_val = max(spec.values) if spec.values else 1
    max_label_width = max(len(lb) for lb in spec.labels)

    for label, value in zip(spec.labels, spec.values):
        if max_val > 0:
            fill = int(value / max_val * width + 0.5)
        else:
            fill = 0
        fill = max(0, min(width, fill))
        empty = width - fill

        row_chars = ["█"] * fill + ["·"] * empty
        padded = label.ljust(max_label_width)
        val_str = str(int(value)) if value == int(value) else str(value)
        lines.append(f"{padded}  |{rle_encode(row_chars)}| {val_str}")

    lines.append("---")
    return "\n".join(lines)


# 8 Unicode block levels for sparklines
_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def compact_line(spec: LineSpec, width: int = 60) -> str:
    """Render a LineSpec as compact sparklines."""
    lines: list[str] = []
    lines.append(f"[COMPACT:line] {spec.title}")

    n_pts = len(spec.x_values)
    if spec.x_is_date and n_pts >= 2:
        lines.append(f"x: {spec.x_values[0]} .. {spec.x_values[-1]} ({n_pts} pts)")
    else:
        lines.append(f"x: ({n_pts} pts)")

    lines.append("---")

    if not spec.y_series:
        lines.append("(no data)")
        lines.append("---")
        return "\n".join(lines)

    max_name_width = max(len(n) for n in spec.y_series)

    for name, values in spec.y_series.items():
        # Downsample if needed
        if len(values) > width:
            chunk_size = len(values) / width
            downsampled = []
            for i in range(width):
                start = int(i * chunk_size)
                end = int((i + 1) * chunk_size)
                downsampled.append(sum(values[start:end]) / (end - start))
            values = downsampled

        v_min = min(values)
        v_max = max(values)
        v_range = v_max - v_min

        sparkline_chars = []
        for v in values:
            if v_range == 0:
                idx = len(_SPARK_CHARS) // 2
            else:
                idx = int((v - v_min) / v_range * (len(_SPARK_CHARS) - 1) + 0.5)
            idx = max(0, min(len(_SPARK_CHARS) - 1, idx))
            sparkline_chars.append(_SPARK_CHARS[idx])

        sparkline = "".join(sparkline_chars)
        padded = f"{name}:".ljust(max_name_width + 1)
        lines.append(f"{padded} {sparkline} (min={v_min:.4g} max={v_max:.4g})")

    lines.append("---")
    return "\n".join(lines)


def compact_bubble(spec: BubbleSpec, title: str = "csvplot") -> str:
    """Render a BubbleSpec as compact presence/absence matrix."""
    lines: list[str] = []
    lines.append(f"[COMPACT:bubble] {title}")

    if not spec.y_labels:
        lines.append("---")
        lines.append("(no data)")
        lines.append("---")
        return "\n".join(lines)

    lines.append("cols: " + " | ".join(spec.col_names))
    lines.append("---")

    max_label_width = max(len(lb) for lb in spec.y_labels)

    for row_idx, label in enumerate(spec.y_labels):
        cells = "".join("●" if val else "·" for val in spec.matrix[row_idx])
        padded = label.rjust(max_label_width)
        lines.append(f"{padded}  |{cells}|")

    lines.append("---")
    return "\n".join(lines)


def compact_summarise(
    summaries: list[ColumnSummary],
    title: str = "csvplot",
    sample_rows: list[dict[str, str]] | None = None,
) -> str:
    """Render column summaries as compact tabular text."""
    lines: list[str] = []
    lines.append(f"[COMPACT:summarise] {title}")

    if not summaries:
        lines.append("---")
        lines.append("(no data)")
        lines.append("---")
        return "\n".join(lines)

    lines.append(f"rows: {summaries[0].row_count}")
    lines.append("---")

    # Build table rows
    headers = ["Column", "Type", "Non-null", "Unique", "Min", "Max", "Top Values (freq)"]
    rows: list[list[str]] = []
    for s in summaries:
        top_str = ""
        if s.high_cardinality:
            top_str = ">10K unique"
        elif s.top_values:
            top_str = ", ".join(f"{v}({c})" for v, c in s.top_values[:5])

        rows.append(
            [
                s.name,
                s.detected_type,
                str(s.non_null_count),
                str(s.unique_count),
                s.min_val or "-",
                s.max_val or "-",
                top_str or "-",
            ]
        )

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    def _fmt_row(cells: list[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            if i in (2, 3):  # Non-null, Unique — right-align
                parts.append(cell.rjust(col_widths[i]))
            else:
                parts.append(cell.ljust(col_widths[i]))
        return " | ".join(parts)

    lines.append(_fmt_row(headers))
    for row in rows:
        lines.append(_fmt_row(row))

    lines.append("---")

    # Sample rows
    if sample_rows:
        lines.append(f"Sample ({len(sample_rows)} rows)")
        cols = list(sample_rows[0].keys())
        sample_widths = [len(c) for c in cols]
        for row in sample_rows:
            for i, c in enumerate(cols):
                sample_widths[i] = max(sample_widths[i], len(str(row.get(c, ""))))

        lines.append(" | ".join(c.ljust(sample_widths[i]) for i, c in enumerate(cols)))
        for row in sample_rows:
            lines.append(
                " | ".join(str(row.get(c, "")).ljust(sample_widths[i]) for i, c in enumerate(cols))
            )

    return "\n".join(lines)
