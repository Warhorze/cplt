"""Tab-completion for column names from CSV headers."""

from __future__ import annotations

import csv
import difflib
from pathlib import Path

import click

from csvplot.reader import detect_date_columns, read_csv_header

# Cache: (resolved_path, mtime) → list of column names
_header_cache: dict[tuple[str, float], list[str]] = {}
_date_col_cache: dict[tuple[str, float], list[str]] = {}
# Cache: (resolved_path, mtime, column_name) → list of distinct values
_value_cache: dict[tuple[str, float, str], list[str]] = {}

SAMPLE_ROWS_FOR_VALUES = 1000

_START_KEYWORDS = {"start", "begin", "van", "from", "first"}
_END_KEYWORDS = {"end", "eind", "stop", "last", "final", "tot", "until"}


def _cache_key(file_path: str | Path) -> tuple[str, float] | None:
    path = Path(file_path)
    if not path.is_file():
        return None
    return (str(path.resolve()), path.stat().st_mtime)


def _get_columns(file_path: str | Path | None) -> list[str]:
    """Get column names from a CSV file, with caching by path + mtime."""
    if not file_path:
        return []
    key = _cache_key(file_path)
    if key is None:
        return []
    if key not in _header_cache:
        try:
            _header_cache[key] = read_csv_header(file_path)
        except Exception:
            return []
    return _header_cache[key]


def _get_date_columns(file_path: str | Path | None) -> list[str]:
    """Get only date-parseable column names, with caching."""
    if not file_path:
        return []
    key = _cache_key(file_path)
    if key is None:
        return []
    if key not in _date_col_cache:
        try:
            _date_col_cache[key] = detect_date_columns(file_path)
        except Exception:
            return []
    return _date_col_cache[key]


def _matches_keywords(column: str, keywords: set[str]) -> bool:
    """Check if a column name contains any of the given keywords (case-insensitive)."""
    col_lower = column.lower()
    return any(kw in col_lower for kw in keywords)


def _sort_columns_for_position(columns: list[str], position: int) -> list[str]:
    """Sort columns with positional awareness for --x completion.

    Even positions (0, 2, 4) = start columns first.
    Odd positions (1, 3, 5) = end columns first.
    """
    if position % 2 == 0:
        preferred_keywords = _START_KEYWORDS
    else:
        preferred_keywords = _END_KEYWORDS

    preferred = sorted(c for c in columns if _matches_keywords(c, preferred_keywords))
    rest = sorted(c for c in columns if not _matches_keywords(c, preferred_keywords))
    return preferred + rest


def complete_column(ctx: click.Context, args: list[str], incomplete: str) -> list[str]:
    """Typer/Click autocompletion callback for all column-name options."""
    file_path = ctx.params.get("file")
    columns = _get_columns(file_path)
    return [c for c in columns if c.lower().startswith(incomplete.lower())]


def complete_date_column(ctx: click.Context, args: list[str], incomplete: str) -> list[str]:
    """Typer/Click autocompletion callback for date column options with smart ordering."""
    file_path = ctx.params.get("file")
    columns = _get_date_columns(file_path)

    # Determine current position in --x values for smart ordering
    x_values = ctx.params.get("x")
    position = len(x_values) if x_values else 0

    filtered = [c for c in columns if c.lower().startswith(incomplete.lower())]
    return _sort_columns_for_position(filtered, position)


def _get_column_values(
    file_path: str | Path, column: str, max_rows: int = SAMPLE_ROWS_FOR_VALUES
) -> list[str]:
    """Get distinct values for a column, sampled from first N rows, with caching."""
    key = _cache_key(file_path)
    if key is None:
        return []
    cache_key = (key[0], key[1], column)
    if cache_key not in _value_cache:
        try:
            seen: set[str] = set()
            values: list[str] = []
            with open(file_path, newline="") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    val = row.get(column, "").strip()
                    if val and val not in seen:
                        seen.add(val)
                        values.append(val)
            _value_cache[cache_key] = values
        except Exception:
            return []
    return _value_cache[cache_key]


def match_values(incomplete: str, values: list[str]) -> list[str]:
    """Match incomplete input against a list of values.

    Strategy: prefix match first, then substring, then difflib for typos.
    """
    if not incomplete:
        return list(values)

    lower = incomplete.lower()

    # 1. Prefix match
    prefix = [v for v in values if v.lower().startswith(lower)]
    if prefix:
        return prefix

    # 2. Substring match
    substr = [v for v in values if lower in v.lower()]
    if substr:
        return substr

    # 3. Typo tolerance via difflib
    close = difflib.get_close_matches(incomplete, values, n=5, cutoff=0.6)
    return list(close)


def _last_context_column(ctx: click.Context) -> str | None:
    """Find the last --x or --y column from context params for pre-filling."""
    # Check --y first (more specific), then --x
    for param in ("y", "x"):
        vals = ctx.params.get(param)
        if vals:
            if isinstance(vals, list) and vals:
                return vals[-1]
            elif isinstance(vals, str):
                return vals
    return None


def complete_where(ctx: click.Context, args: list[str], incomplete: str) -> list[str]:
    """Typer/Click autocompletion callback for --where values.

    Context-aware: pre-fills column name from the last --x/--y.
    """
    file_path = ctx.params.get("file")
    if not file_path:
        return []

    try:
        columns = _get_columns(file_path)
    except Exception:
        return []

    if not columns:
        return []

    if "=" in incomplete:
        # User typed COL=partial — suggest values for that column
        col, partial = incomplete.split("=", 1)
        col_map = {c.lower(): c for c in columns}
        actual_col = col_map.get(col.lower())
        if actual_col is None:
            return []
        values = _get_column_values(file_path, actual_col)
        matched = match_values(partial, values)
        return [f"{actual_col}={v}" for v in matched]

    # No "=" yet — suggest COL= completions
    # Pre-fill from last --x/--y context column
    context_col = _last_context_column(ctx)
    col_map = {c.lower(): c for c in columns}
    actual_context_col = col_map.get(context_col.lower()) if context_col else None

    suggestions: list[str] = []
    if actual_context_col:
        # Pre-fill with context column values
        values = _get_column_values(file_path, actual_context_col)
        suggestions = [f"{actual_context_col}={v}" for v in values]

    # Also suggest other columns as COL= format
    for col in columns:
        if col != actual_context_col:
            suggestions.append(f"{col}=")

    if incomplete:
        lower = incomplete.lower()
        suggestions = [s for s in suggestions if s.lower().startswith(lower)]

    return suggestions
