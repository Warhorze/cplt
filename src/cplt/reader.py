"""CSV reading and datetime parsing."""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterator, Literal, NoReturn

from rich import print as rprint

from cplt.models import BarSpec, Dot, LineSpec, Segment

DATETIME_FORMATS = [
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y",
]

SENTINEL_YEAR = 9999
MISSING_GROUP = "(missing)"
EMPTY_WHERE_MATCH_VALUES = {"", "null", "none", "na", "nan"}


def _ensure_well_formed_row(row: dict[str, str], row_number: int) -> None:
    """Raise a clear error when DictReader emits malformed rows."""
    if None in row or any(value is None for value in row.values()):
        raise ValueError(
            f"Failed to read CSV: row {row_number} has missing columns. Check file format."
        )


def _raise_missing_column(missing_col: str, row: dict[str, str]) -> NoReturn:
    """Raise a helpful column-not-found error with available options."""
    raise KeyError(f"Column {missing_col!r} not found. Available: {', '.join(sorted(row.keys()))}")


def _ensure_columns_exist(required_cols: list[str], row: dict[str, str]) -> None:
    """Ensure all required columns exist in the row mapping."""
    for col in required_cols:
        if col not in row:
            _raise_missing_column(col, row)


def read_csv_header(path: str | Path) -> list[str]:
    """Read only the first line of a CSV and return column names."""
    with open(path, newline="") as f:
        reader = csv.reader(f)
        return next(reader)


def detect_date_columns(path: str | Path, *, sample_rows: int = 10) -> list[str]:
    """Return column names that have at least one datetime value in the first few rows."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        date_cols: set[str] = set()
        columns: list[str] = []
        for i, row in enumerate(reader):
            if i == 0:
                columns = list(row.keys())
            for col in columns:
                if col not in date_cols and _is_datetime(row.get(col, "")):
                    date_cols.add(col)
            if i + 1 >= sample_rows:
                break
    # Preserve original column order
    return [col for col in columns if col in date_cols]


def detect_numeric_columns(path: str | Path, *, sample_rows: int = 10) -> list[str]:
    """Return column names that have at least one numeric value in the first few rows."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        num_cols: set[str] = set()
        columns: list[str] = []
        for i, row in enumerate(reader):
            if i == 0:
                columns = list(row.keys())
            for col in columns:
                if col not in num_cols and _is_numeric(row.get(col, "")):
                    num_cols.add(col)
            if i + 1 >= sample_rows:
                break
    return [col for col in columns if col in num_cols]


def _is_numeric(value: str) -> bool:
    """Check if a string looks like a number."""
    value = value.strip()
    if not value:
        return False
    try:
        float(value)
        return True
    except ValueError:
        return False


def _is_datetime(value: str) -> bool:
    """Check if a string looks like a datetime (including sentinels)."""
    value = value.strip()
    if not value:
        return False
    for fmt in DATETIME_FORMATS:
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def parse_datetime(value: str) -> datetime | None:
    """Parse a datetime string, returning None for empty or sentinel values."""
    value = value.strip()
    if not value:
        return None
    for fmt in DATETIME_FORMATS:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.year >= SENTINEL_YEAR:
                return None
            return dt
        except ValueError:
            continue
    return None


def parse_where(expr: str) -> tuple[str, str]:
    """Parse a 'COL=val' expression into (column, value).

    Raises ValueError if the format is invalid.
    """
    if "=" not in expr:
        raise ValueError(f"Expected format COL=value, got {expr!r}")
    col, val = expr.split("=", 1)
    if not col:
        raise ValueError(f"Empty column name in {expr!r}")
    if val.strip().lower() == "(empty)":
        val = ""
    return col, val


def _resolve_filter_columns(
    requested_cols: list[str], row: dict[str, str], *, case_sensitive: bool
) -> dict[str, str]:
    """Resolve requested filter columns to actual CSV keys."""
    if case_sensitive:
        missing = [col for col in requested_cols if col not in row]
        if missing:
            _raise_missing_column(missing[0], row)
        return {col: col for col in requested_cols}

    # Case-insensitive column matching, preserving actual key casing.
    key_map = {k.lower(): k for k in row}
    resolved: dict[str, str] = {}
    for col in requested_cols:
        actual = key_map.get(col.lower())
        if actual is None:
            _raise_missing_column(col, row)
        resolved[col] = actual
    return resolved


def filter_rows(
    rows: Iterator[dict[str, str]],
    *,
    wheres: list[tuple[str, str]] | None = None,
    where_nots: list[tuple[str, str]] | None = None,
    case_sensitive: bool = False,
) -> Iterator[dict[str, str]]:
    """Filter CSV rows by where/where-not conditions.

    - Same column repeated in wheres = OR (match any value)
    - Different columns in wheres = AND (all must match)
    - where_nots = exclude rows matching any condition
    - Case-insensitive by default.
    """
    wheres = wheres or []
    where_nots = where_nots or []

    if not wheres and not where_nots:
        yield from rows
        return

    # Group where conditions by column: {col: [val1, val2]} (OR within column)
    where_groups: dict[str, list[str]] = defaultdict(list)
    for col, val in wheres:
        where_groups[col].append(val if case_sensitive else val.lower())

    # Group where-not conditions by column
    where_not_groups: dict[str, list[str]] = defaultdict(list)
    for col, val in where_nots:
        where_not_groups[col].append(val if case_sensitive else val.lower())

    def _matches_values(row_raw: str, vals: list[str]) -> bool:
        if "" in vals and row_raw.strip().lower() in EMPTY_WHERE_MATCH_VALUES:
            return True
        if case_sensitive:
            return row_raw in vals
        return row_raw.lower() in vals

    resolved_cols: dict[str, str] | None = None
    for row in rows:
        # Validate column names on first row and resolve case-insensitive aliases.
        if resolved_cols is None:
            resolved_cols = _resolve_filter_columns(
                list(where_groups) + list(where_not_groups),
                row,
                case_sensitive=case_sensitive,
            )

        # Check where conditions (AND across columns, OR within same column)
        match = True
        for col, vals in where_groups.items():
            actual_col = resolved_cols[col]
            if not _matches_values(row[actual_col], vals):
                match = False
                break

        if not match:
            continue

        # Check where-not conditions (exclude if ANY matches)
        excluded = False
        for col, vals in where_not_groups.items():
            actual_col = resolved_cols[col]
            if _matches_values(row[actual_col], vals):
                excluded = True
                break

        if not excluded:
            yield row


def load_segments(
    path: str | Path,
    x_pairs: list[tuple[str, str]],
    y_col: str | list[str],
    *,
    color_col: str | None = None,
    txt_col: str | None = None,
    y_detail_col: str | None = None,
    open_end: datetime | None = None,
    max_rows: int | None = None,
    wheres: list[tuple[str, str]] | None = None,
    where_nots: list[tuple[str, str]] | None = None,
    case_sensitive: bool = False,
) -> list[Segment]:
    """Load CSV rows into Segment objects.

    Args:
        path: Path to the CSV file.
        x_pairs: List of (start_col, end_col) tuples, one per layer.
        y_col: Column name(s) for categorical Y-axis.
        color_col: Column name for color grouping.
        txt_col: Column name for text labels on segments.
        y_detail_col: Column name to append as detail sub-group to y_label.
        open_end: Replacement date for NULL/sentinel end dates.
        max_rows: Limit processing to the first N CSV rows.
    """
    segments: list[Segment] = []
    skipped_unparseable = 0
    y_cols = [y_col] if isinstance(y_col, str) else list(y_col)

    def _is_open_end_candidate(value: str) -> bool:
        raw = value.strip()
        if not raw:
            return True
        for fmt in DATETIME_FORMATS:
            try:
                return datetime.strptime(raw, fmt).year >= SENTINEL_YEAR
            except ValueError:
                continue
        return False

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows: Iterator[dict[str, str]] = reader
        if wheres or where_nots:
            rows = filter_rows(
                rows, wheres=wheres, where_nots=where_nots, case_sensitive=case_sensitive
            )
        required_cols = [col for pair in x_pairs for col in pair]
        required_cols.extend(y_cols)
        if color_col:
            required_cols.append(color_col)
        if txt_col:
            required_cols.append(txt_col)
        if y_detail_col:
            required_cols.append(y_detail_col)
        for row_index, row in enumerate(rows, start=1):
            _ensure_well_formed_row(row, row_index + 1)
            if row_index == 1:
                _ensure_columns_exist(required_cols, row)
            if max_rows is not None and row_index > max_rows:
                break

            y_label = " | ".join(row[col] for col in y_cols)
            if y_detail_col:
                y_label = f"{y_label} | {row[y_detail_col]}"
            color_key: str | None = None
            if color_col:
                color_raw = row[color_col].strip()
                color_key = color_raw if color_raw else MISSING_GROUP
            txt_label = row[txt_col] if txt_col else ""

            for layer_index, (start_col, end_col) in enumerate(x_pairs):
                start = parse_datetime(row[start_col])
                end = parse_datetime(row[end_col])
                if start is None:
                    if row[start_col].strip() and not _is_open_end_candidate(row[start_col]):
                        skipped_unparseable += 1
                    continue
                if end is None and open_end is not None and _is_open_end_candidate(row[end_col]):
                    end = open_end
                if end is None:
                    if row[end_col].strip() and not _is_open_end_candidate(row[end_col]):
                        skipped_unparseable += 1
                    continue
                if start > end:
                    rprint(
                        f"[yellow]Warning:[/yellow] start > end in row "
                        f"(y={y_label!r}, layer={layer_index}), swapping."
                    )
                    start, end = end, start
                segments.append(
                    Segment(
                        row_index=row_index,
                        layer=layer_index,
                        y_label=y_label,
                        start=start,
                        end=end,
                        color_key=color_key,
                        txt_label=txt_label,
                    )
                )

    if skipped_unparseable > 0:
        sys.stderr.write(f"Warning: skipped {skipped_unparseable} row(s) with unparseable dates\n")

    return segments


def load_dots(
    path: str | Path,
    dot_cols: list[str],
    y_col: list[str],
    *,
    color_col: str | None = None,
    max_rows: int | None = None,
    wheres: list[tuple[str, str]] | None = None,
    where_nots: list[tuple[str, str]] | None = None,
    case_sensitive: bool = False,
) -> list[Dot]:
    """Load per-row single-date dots from CSV columns.

    Each dot_col is a date column; each produces dots at layer 0, 1, etc.
    Rows with empty/unparseable dates in a given column are skipped for that column.
    """
    dots: list[Dot] = []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows: Iterator[dict[str, str]] = reader
        if wheres or where_nots:
            rows = filter_rows(
                rows, wheres=wheres, where_nots=where_nots, case_sensitive=case_sensitive
            )
        required_cols = list(dot_cols) + list(y_col)
        if color_col:
            required_cols.append(color_col)
        for row_index, row in enumerate(rows, start=1):
            _ensure_well_formed_row(row, row_index + 1)
            if row_index == 1:
                _ensure_columns_exist(required_cols, row)
            if max_rows is not None and row_index > max_rows:
                break

            y_label = " | ".join(row[col] for col in y_col)
            color_key: str | None = None
            if color_col:
                color_raw = row[color_col].strip()
                color_key = color_raw if color_raw else MISSING_GROUP

            for layer_index, dot_col in enumerate(dot_cols):
                dt = parse_datetime(row[dot_col])
                if dt is None:
                    continue
                dots.append(
                    Dot(
                        row_index=row_index,
                        layer=layer_index,
                        y_label=y_label,
                        date=dt,
                        color_key=color_key,
                    )
                )

    return dots


def load_bar_data(
    path: str | Path,
    column: str,
    *,
    sort_by: Literal["value", "label", "none"] = "value",
    top: int | None = None,
    max_rows: int | None = None,
    title: str = "cplt",
    horizontal: bool = False,
    show_labels: bool = False,
    wheres: list[tuple[str, str]] | None = None,
    where_nots: list[tuple[str, str]] | None = None,
    case_sensitive: bool = False,
) -> BarSpec:
    """Count distinct values in a column and return a BarSpec.

    Args:
        path: Path to the CSV file.
        column: Column name to count values of.
        sort_by: Sort order — "value" (descending count), "label" (alpha), "none" (CSV order).
        top: Show only the top N categories.
        max_rows: Limit CSV rows read.
        title: Chart title.
        horizontal: Use horizontal bars.
    """
    counts: dict[str, int] = {}
    order: list[str] = []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows: Iterator[dict[str, str]] = reader
        if wheres or where_nots:
            rows = filter_rows(
                rows, wheres=wheres, where_nots=where_nots, case_sensitive=case_sensitive
            )
        for i, row in enumerate(rows, start=1):
            _ensure_well_formed_row(row, i + 1)
            if i == 1:
                _ensure_columns_exist([column], row)
            if max_rows is not None and i > max_rows:
                break
            raw_val = row[column]
            val = raw_val if raw_val.strip() else MISSING_GROUP
            if val not in counts:
                order.append(val)
                counts[val] = 0
            counts[val] += 1

    if sort_by not in {"value", "label", "none"}:
        raise ValueError(f"Invalid sort_by {sort_by!r}; expected 'value', 'label', or 'none'.")

    # Always select top N by count first, then apply sort to the selected set
    if top is not None:
        order.sort(key=lambda k: counts[k], reverse=True)
        order = order[:top]

    if sort_by == "value":
        order.sort(key=lambda k: counts[k], reverse=True)
    elif sort_by == "label":
        order.sort()

    return BarSpec(
        labels=order,
        values=[float(counts[k]) for k in order],
        title=title,
        horizontal=horizontal,
        show_labels=show_labels,
    )


def load_line_data(
    path: str | Path,
    x_col: str,
    y_cols: list[str],
    *,
    color_col: str | None = None,
    max_rows: int | None = None,
    title: str = "cplt",
    wheres: list[tuple[str, str]] | None = None,
    where_nots: list[tuple[str, str]] | None = None,
    case_sensitive: bool = False,
) -> LineSpec:
    """Extract x/y pairs for line plotting, optionally grouped by a color column.

    Args:
        path: Path to the CSV file.
        x_col: Column for the X axis (date or sequential).
        y_cols: Column(s) for the Y axis (numeric).
        color_col: Optional column to split into separate series.
        max_rows: Limit CSV rows read.
        title: Chart title.
    """
    raw_rows: list[dict[str, str]] = []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows: Iterator[dict[str, str]] = reader
        if wheres or where_nots:
            rows = filter_rows(
                rows, wheres=wheres, where_nots=where_nots, case_sensitive=case_sensitive
            )
        required_cols = [x_col, *y_cols]
        if color_col:
            required_cols.append(color_col)
        for i, row in enumerate(rows, start=1):
            _ensure_well_formed_row(row, i + 1)
            if i == 1:
                _ensure_columns_exist(required_cols, row)
            if max_rows is not None and i > max_rows:
                break
            raw_rows.append(row)

    if not raw_rows:
        return LineSpec(title=title)

    # Detect if x column contains dates
    x_is_date = any(parse_datetime(row[x_col]) is not None for row in raw_rows[:10])

    # Sort by date if applicable
    if x_is_date:
        # Drop rows with invalid/blank dates to avoid renderer crashes in date mode.
        raw_rows = [row for row in raw_rows if parse_datetime(row[x_col]) is not None]
        raw_rows.sort(key=lambda r: parse_datetime(r[x_col]) or datetime.min)

    if not raw_rows:
        return LineSpec(title=title, x_is_date=x_is_date)

    # Build series: either grouped by color_col, or one series per y_col
    series: dict[str, list[float]] = {}
    x_values: list[str] = []

    if color_col:
        # When grouping by color, we need a single y column
        y_col = y_cols[0]
        # Collect all unique x values in order
        groups: dict[str, dict[str, float]] = {}
        x_set: list[str] = []
        x_seen: set[str] = set()
        for row in raw_rows:
            x_val = row[x_col]
            if x_val not in x_seen:
                x_set.append(x_val)
                x_seen.add(x_val)
            group_key = row[color_col]
            if group_key not in groups:
                groups[group_key] = {}
            try:
                groups[group_key][x_val] = float(row[y_col])
            except (ValueError, TypeError):
                continue

        x_values = x_set
        for group_key, vals in groups.items():
            series[group_key] = [vals.get(x, float("nan")) for x in x_values]
    else:
        x_values = [row[x_col] for row in raw_rows]
        for y_col in y_cols:
            y_vals: list[float] = []
            for row in raw_rows:
                try:
                    y_vals.append(float(row[y_col]))
                except (ValueError, TypeError):
                    y_vals.append(float("nan"))
            series[y_col] = y_vals

    return LineSpec(
        x_values=x_values,
        y_series=series,
        title=title,
        x_is_date=x_is_date,
    )
