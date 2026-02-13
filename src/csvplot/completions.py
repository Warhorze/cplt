"""Tab-completion for column names from CSV headers."""

from __future__ import annotations

from pathlib import Path

import click

from csvplot.reader import detect_date_columns, read_csv_header

# Cache: (resolved_path, mtime) → list of column names
_header_cache: dict[tuple[str, float], list[str]] = {}
_date_col_cache: dict[tuple[str, float], list[str]] = {}

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
