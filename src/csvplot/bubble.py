"""Bubble matrix data loading — presence/absence dot matrix from CSV."""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from csvplot.reader import _ensure_columns_exist, filter_rows

FALSY_VALUES = frozenset({"", "0", "false", "no", "null", "none", "na", "nan"})


@dataclass
class BubbleSpec:
    y_labels: list[str] = field(default_factory=list)
    col_names: list[str] = field(default_factory=list)
    matrix: list[list[bool]] = field(default_factory=list)
    color_keys: list[str] = field(default_factory=list)
    total_rows: int = 0


def is_falsy(value: str) -> bool:
    """Check if a value is considered falsy for bubble matrix purposes."""
    return value.strip().lower() in FALSY_VALUES


def load_bubble_data(
    path: str | Path,
    cols: list[str],
    y_col: str,
    *,
    color_col: str | None = None,
    max_rows: int | None = None,
    sample_n: int | None = None,
    top: int | None = None,
    wheres: list[tuple[str, str]] | None = None,
    where_nots: list[tuple[str, str]] | None = None,
    case_sensitive: bool = False,
) -> BubbleSpec:
    """Load CSV and build a presence/absence matrix.

    Args:
        path: Path to CSV file.
        cols: Columns to check for presence/absence.
        y_col: Column for row labels.
        color_col: Optional column for color grouping.
        max_rows: Limit input rows.
        top: Keep only the top N columns by fill-rate.
        wheres: Filter conditions.
        where_nots: Exclusion conditions.
        case_sensitive: Whether filters are case-sensitive.
    """
    selected_rows: list[dict[str, str]] = []
    total_rows = 0

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows: Iterator[dict[str, str]] = reader
        if wheres or where_nots:
            rows = filter_rows(
                rows, wheres=wheres, where_nots=where_nots, case_sensitive=case_sensitive
            )

        required_cols = [*cols, y_col]
        if color_col:
            required_cols.append(color_col)

        for row_index, row in enumerate(rows, start=1):
            if row_index == 1:
                _ensure_columns_exist(required_cols, row)
            total_rows += 1
            if max_rows is not None and len(selected_rows) >= max_rows:
                continue
            selected_rows.append(row)

    if sample_n is not None and sample_n < len(selected_rows):
        selected_rows = random.sample(selected_rows, sample_n)

    y_labels: list[str] = []
    color_keys: list[str] = []
    raw_matrix: list[list[bool]] = []
    for row in selected_rows:
        y_labels.append(row[y_col])
        if color_col:
            color_keys.append(row[color_col])
        raw_matrix.append([not is_falsy(row[col]) for col in cols])

    # Apply --top N by fill-rate
    active_cols = list(range(len(cols)))
    if top is not None and top < len(cols) and raw_matrix:
        fill_rates = []
        for col_idx in range(len(cols)):
            truthy = sum(1 for row in raw_matrix if row[col_idx])
            fill_rates.append((truthy, col_idx))
        fill_rates.sort(key=lambda x: x[0], reverse=True)
        active_cols = [idx for _, idx in fill_rates[:top]]

    col_names = [cols[i] for i in active_cols]
    matrix = [[row[i] for i in active_cols] for row in raw_matrix]

    return BubbleSpec(
        y_labels=y_labels,
        col_names=col_names,
        matrix=matrix,
        color_keys=color_keys,
        total_rows=total_rows,
    )
