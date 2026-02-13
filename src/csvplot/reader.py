"""CSV reading and datetime parsing."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from rich import print as rprint

from csvplot.models import Segment

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


def load_segments(
    path: str | Path,
    x_pairs: list[tuple[str, str]],
    y_col: str | list[str],
    *,
    color_col: str | None = None,
    txt_col: str | None = None,
    open_end: datetime | None = None,
    max_rows: int | None = None,
) -> list[Segment]:
    """Load CSV rows into Segment objects.

    Args:
        path: Path to the CSV file.
        x_pairs: List of (start_col, end_col) tuples, one per layer.
        y_col: Column name(s) for categorical Y-axis.
        color_col: Column name for color grouping.
        txt_col: Column name for text labels on segments.
        open_end: Replacement date for NULL/sentinel end dates.
        max_rows: Limit processing to the first N CSV rows.
    """
    segments: list[Segment] = []
    y_cols = [y_col] if isinstance(y_col, str) else list(y_col)

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row_index, row in enumerate(reader, start=1):
            if max_rows is not None and row_index > max_rows:
                break

            y_label = " | ".join(row[col] for col in y_cols)
            color_key = row[color_col] if color_col else ""
            txt_label = row[txt_col] if txt_col else ""

            for layer_index, (start_col, end_col) in enumerate(x_pairs):
                start = parse_datetime(row[start_col])
                end = parse_datetime(row[end_col])
                if start is not None:
                    if end is None and open_end is not None:
                        end = open_end
                    if end is not None:
                        if start > end:
                            rprint(
                                f"[yellow]Warning:[/yellow] start > end in row "
                                f"(y={y_label!r}, layer={layer_index}), swapping."
                            )
                            start, end = end, start
                        segments.append(
                            Segment(
                                layer=layer_index,
                                y_label=y_label,
                                start=start,
                                end=end,
                                color_key=color_key,
                                txt_label=txt_label,
                            )
                        )

    return segments
