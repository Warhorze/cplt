"""Summarise CSV data — column types, counts, nulls, unique values, top values."""

from __future__ import annotations

import csv
import math
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal, overload

from cplt.reader import filter_rows, parse_datetime

MAX_DISTINCT_VALUES = 10_000
NUMERIC_THRESHOLD = 0.80
DATE_THRESHOLD = 0.80

NULL_SENTINELS = frozenset(
    {
        "NA",
        "N/A",
        "NaN",
        "nan",
        "null",
        "NULL",
        "None",
        "none",
        "#N/A",
        "#NA",
        "-",
        '""',
        "''",
        "``",
    }
)

# Date format patterns: (regex, label)
_DATE_FORMAT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+$"), "YYYY-MM-DDTHH:MM:SS.f"),
    (re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$"), "YYYY-MM-DDTHH:MM:SS"),
    (re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+$"), "YYYY-MM-DD HH:MM:SS.f"),
    (re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"), "YYYY-MM-DD HH:MM:SS"),
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "YYYY-MM-DD"),
    (re.compile(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}$"), "DD-MM-YYYY HH:MM:SS"),
    (re.compile(r"^\d{2}-\d{2}-\d{4}$"), "DD-MM-YYYY"),
    (re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2}$"), "DD/MM/YYYY HH:MM:SS"),
    (re.compile(r"^\d{2}/\d{2}/\d{4}$"), "DD/MM/YYYY"),
]

MIXED_TYPE_THRESHOLD = 0.95


def _guess_date_format(raw: str) -> str:
    """Classify a raw date string into a format pattern label."""
    for pattern, label in _DATE_FORMAT_PATTERNS:
        if pattern.match(raw):
            return label
    return "other"


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
    # Data-quality fields
    null_count: int = 0
    null_sentinel_count: int = 0
    zero_count: int = 0
    mean: float | None = None
    stddev: float | None = None
    date_formats: list[tuple[str, int]] = field(default_factory=list)
    whitespace_count: int = 0
    mixed_type_pct: str = ""
    mixed_type_examples: list[str] = field(default_factory=list)


@overload
def summarise_csv(
    path: str | Path,
    *,
    wheres: list[tuple[str, str]] | None = ...,
    where_nots: list[tuple[str, str]] | None = ...,
    case_sensitive: bool = ...,
    max_rows: int | None = ...,
    sample_n: int | None = ...,
    return_sample: Literal[False] = ...,
) -> list[ColumnSummary]: ...


@overload
def summarise_csv(
    path: str | Path,
    *,
    wheres: list[tuple[str, str]] | None = ...,
    where_nots: list[tuple[str, str]] | None = ...,
    case_sensitive: bool = ...,
    max_rows: int | None = ...,
    sample_n: int,
    return_sample: Literal[True],
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

    # Data-quality tracking
    sentinel_count: dict[str, int] = {}
    zero_count: dict[str, int] = {}
    numeric_sum: dict[str, float] = {}
    numeric_sum_sq: dict[str, float] = {}
    date_format_counters: dict[str, Counter[str]] = {}
    whitespace_count: dict[str, int] = {}
    # Exclusive type counts for mixed-type detection (each value → exactly one type)
    exclusive_numeric: dict[str, int] = {}
    exclusive_date: dict[str, int] = {}
    exclusive_text: dict[str, int] = {}
    # Minority-type examples (small set per column)
    minority_examples: dict[str, set[str]] = {}

    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or [])
        for col in columns:
            counters[col] = Counter()
            non_null[col] = 0
            numeric_count[col] = 0
            date_count[col] = 0
            capped[col] = False
            sentinel_count[col] = 0
            zero_count[col] = 0
            numeric_sum[col] = 0.0
            numeric_sum_sq[col] = 0.0
            date_format_counters[col] = Counter()
            whitespace_count[col] = 0
            exclusive_numeric[col] = 0
            exclusive_date[col] = 0
            exclusive_text[col] = 0
            minority_examples[col] = set()

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

                # Whitespace check (non-empty after strip but had leading/trailing)
                if val != stripped:
                    whitespace_count[col] += 1

                # Null sentinel check
                if stripped in NULL_SENTINELS:
                    sentinel_count[col] += 1

                # Track distinct values up to cap
                if not capped[col]:
                    counters[col][stripped] += 1
                    if len(counters[col]) > MAX_DISTINCT_VALUES:
                        capped[col] = True

                # Numeric check
                is_numeric = False
                try:
                    fval = float(stripped)
                    is_numeric = True
                    numeric_count[col] += 1
                    numeric_sum[col] += fval
                    numeric_sum_sq[col] += fval * fval
                    if fval == 0.0:
                        zero_count[col] += 1
                    if col not in numeric_min or fval < numeric_min[col]:
                        numeric_min[col] = fval
                    if col not in numeric_max or fval > numeric_max[col]:
                        numeric_max[col] = fval
                except ValueError:
                    pass

                # Date check
                is_date = False
                dt = parse_datetime(stripped)
                if dt is not None:
                    is_date = True
                    date_count[col] += 1
                    dt_str = dt.isoformat()
                    if col not in date_min or dt_str < date_min[col]:
                        date_min[col] = dt_str
                    if col not in date_max or dt_str > date_max[col]:
                        date_max[col] = dt_str
                    date_format_counters[col][_guess_date_format(stripped)] += 1

                # Exclusive type classification: numeric > date > text
                if is_numeric:
                    exclusive_numeric[col] += 1
                elif is_date:
                    exclusive_date[col] += 1
                else:
                    exclusive_text[col] += 1

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

        # Data-quality fields
        s.null_count = row_count - nn
        s.null_sentinel_count = sentinel_count[col]
        s.whitespace_count = whitespace_count[col]

        # Numeric fields (any column with numeric values)
        nc = numeric_count[col]
        if nc > 0:
            s.zero_count = zero_count[col]
            s.mean = numeric_sum[col] / nc
            variance = (numeric_sum_sq[col] / nc) - (s.mean * s.mean)
            s.stddev = math.sqrt(max(0.0, variance))

        # Date formats (any column with date values)
        if date_format_counters[col]:
            s.date_formats = date_format_counters[col].most_common()

        # Mixed type detection (using exclusive counts)
        if nn > 0:
            exc_n = exclusive_numeric[col]
            exc_d = exclusive_date[col]
            exc_t = exclusive_text[col]
            dominant = max(exc_n, exc_d, exc_t)
            if dominant / nn < MIXED_TYPE_THRESHOLD:
                # Build percentage string for types with >0 count
                parts = []
                for label, count in [
                    ("numeric", exc_n),
                    ("date", exc_d),
                    ("text", exc_t),
                ]:
                    if count > 0:
                        pct = round(100 * count / nn)
                        parts.append(f"{pct}% {label}")
                s.mixed_type_pct = ", ".join(parts)

                # Collect minority examples: values NOT in the dominant type
                dominant_type = (
                    "numeric" if exc_n == dominant else "date" if exc_d == dominant else "text"
                )
                # Scan counters for minority examples
                if not capped[col]:
                    for val in counters[col]:
                        if len(minority_examples[col]) >= 3:
                            break
                        is_num = False
                        try:
                            float(val)
                            is_num = True
                        except ValueError:
                            pass
                        is_dt = parse_datetime(val) is not None
                        # Exclusive classification
                        if is_num:
                            val_type = "numeric"
                        elif is_dt:
                            val_type = "date"
                        else:
                            val_type = "text"
                        if val_type != dominant_type:
                            minority_examples[col].add(val)
                s.mixed_type_examples = sorted(minority_examples[col])[:3]

        summaries.append(s)

    if return_sample and sample_n:
        if sample_n >= len(all_rows):
            sample = all_rows
        else:
            sample = random.sample(all_rows, sample_n)
        return summaries, sample

    return summaries
