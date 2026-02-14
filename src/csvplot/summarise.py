"""Summarise CSV data — column types, counts, nulls, unique values, top values."""

from __future__ import annotations

import csv
import random
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, overload

from csvplot.reader import filter_rows, parse_datetime

MAX_DISTINCT_VALUES = 10_000
NUMERIC_THRESHOLD = 0.80
DATE_THRESHOLD = 0.80


@dataclass
class ColumnSummary:
    name: str
    detected_type: str = "text"  # "text", "numeric", "date"
    row_count: int = 0
    non_null_count: int = 0
    unique_count: int = 0
    min_val: str = ""
    max_val: str = ""
    top_values: list[tuple[str, int]] = field(default_factory=list)
    high_cardinality: bool = False


@overload
def summarise_csv(
    path: str | Path,
    *,
    wheres: list[tuple[str, str]] | None = ...,
    where_nots: list[tuple[str, str]] | None = ...,
    case_sensitive: bool = ...,
    max_rows: int | None = ...,
    sample_n: int | None = ...,
    return_sample: bool = ...,
) -> list[ColumnSummary]: ...


@overload
def summarise_csv(
    path: str | Path,
    *,
    wheres: list[tuple[str, str]] | None = ...,
    where_nots: list[tuple[str, str]] | None = ...,
    case_sensitive: bool = ...,
    max_rows: int | None = ...,
    sample_n: int = ...,
    return_sample: bool = ...,
) -> tuple[list[ColumnSummary], list[dict[str, str]]]: ...


def summarise_csv(
    path: str | Path,
    *,
    wheres: list[tuple[str, str]] | None = None,
    where_nots: list[tuple[str, str]] | None = None,
    case_sensitive: bool = False,
    max_rows: int | None = None,
    sample_n: int | None = None,
    return_sample: bool = False,
) -> list[ColumnSummary] | tuple[list[ColumnSummary], list[dict[str, str]]]:
    """Summarise a CSV file, returning per-column stats.

    Args:
        path: Path to CSV file.
        wheres: Filter conditions (col, val) pairs.
        where_nots: Exclusion conditions.
        case_sensitive: Whether filters are case-sensitive.
        max_rows: Limit input rows (--head).
        sample_n: Number of random sample rows to return.
        return_sample: If True, return (summaries, sample_rows) tuple.
    """
    columns: list[str] = []
    counters: dict[str, Counter[str]] = {}
    non_null: dict[str, int] = {}
    numeric_count: dict[str, int] = {}
    date_count: dict[str, int] = {}
    numeric_min: dict[str, float] = {}
    numeric_max: dict[str, float] = {}
    date_min: dict[str, str] = {}
    date_max: dict[str, str] = {}
    capped: dict[str, bool] = {}
    row_count = 0
    all_rows: list[dict[str, str]] = [] if (sample_n and return_sample) else []

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or [])
        for col in columns:
            counters[col] = Counter()
            non_null[col] = 0
            numeric_count[col] = 0
            date_count[col] = 0
            capped[col] = False

        rows: Iterator[dict[str, str]] = reader
        if wheres or where_nots:
            rows = filter_rows(
                rows, wheres=wheres, where_nots=where_nots, case_sensitive=case_sensitive
            )

        for i, row in enumerate(rows, start=1):
            if max_rows is not None and i > max_rows:
                break

            row_count += 1

            if sample_n and return_sample:
                all_rows.append(row)

            for col in columns:
                val = row[col]
                stripped = val.strip()

                if not stripped:
                    continue

                non_null[col] += 1

                # Track distinct values up to cap
                if not capped[col]:
                    counters[col][stripped] += 1
                    if len(counters[col]) > MAX_DISTINCT_VALUES:
                        capped[col] = True

                # Numeric check
                try:
                    fval = float(stripped)
                    numeric_count[col] += 1
                    if col not in numeric_min or fval < numeric_min[col]:
                        numeric_min[col] = fval
                    if col not in numeric_max or fval > numeric_max[col]:
                        numeric_max[col] = fval
                except ValueError:
                    pass

                # Date check
                dt = parse_datetime(stripped)
                if dt is not None:
                    date_count[col] += 1
                    dt_str = dt.isoformat()
                    if col not in date_min or dt_str < date_min[col]:
                        date_min[col] = dt_str
                    if col not in date_max or dt_str > date_max[col]:
                        date_max[col] = dt_str

    # Build summaries
    summaries: list[ColumnSummary] = []
    for col in columns:
        nn = non_null[col]
        s = ColumnSummary(name=col, row_count=row_count)
        s.non_null_count = nn
        s.high_cardinality = capped[col]
        s.unique_count = len(counters[col])

        # Type detection: >80% of non-null values
        if nn > 0:
            if numeric_count[col] / nn >= NUMERIC_THRESHOLD:
                s.detected_type = "numeric"
                s.min_val = str(numeric_min.get(col, ""))
                s.max_val = str(numeric_max.get(col, ""))
            elif date_count[col] / nn >= DATE_THRESHOLD:
                s.detected_type = "date"
                s.min_val = date_min.get(col, "")
                s.max_val = date_max.get(col, "")
            else:
                s.detected_type = "text"

        # Top 5 values
        if not capped[col]:
            s.top_values = counters[col].most_common(5)

        summaries.append(s)

    if return_sample and sample_n:
        if sample_n >= len(all_rows):
            sample = all_rows
        else:
            sample = random.sample(all_rows, sample_n)
        return summaries, sample

    return summaries
