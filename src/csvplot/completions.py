"""Tab-completion for column names from CSV headers."""

from __future__ import annotations

import csv
import difflib
from pathlib import Path
from typing import Any

import click
import typer._completion_shared as _typer_completion

from csvplot.reader import detect_date_columns, read_csv_header

# Cache: (resolved_path, mtime) → list of column names
_header_cache: dict[tuple[str, float], list[str]] = {}
_date_col_cache: dict[tuple[str, float], list[str]] = {}
# Cache: (resolved_path, mtime, column_name) → list of distinct values
_value_cache: dict[tuple[str, float, str], list[str]] = {}

SAMPLE_ROWS_FOR_VALUES = 1000

_START_KEYWORDS = {"start", "begin", "van", "from", "first"}
_END_KEYWORDS = {"end", "eind", "stop", "last", "final", "tot", "until"}


def _ctx_file_path(ctx: click.Context) -> str | Path | None:
    value: Any = ctx.params.get("file")
    if isinstance(value, (str, Path)):
        return value
    return None


def _ctx_param_values(ctx: click.Context, name: str) -> list[str]:
    value: Any = ctx.params.get(name)
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _cache_key(file_path: str | Path) -> tuple[str, float] | None:
    path = Path(file_path).expanduser()
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
            _header_cache[key] = read_csv_header(key[0])
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
            _date_col_cache[key] = detect_date_columns(key[0])
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
    _ = args
    file_path = _ctx_file_path(ctx)
    columns = _get_columns(file_path)
    return [c for c in columns if c.lower().startswith(incomplete.lower())]


def complete_date_column(ctx: click.Context, args: list[str], incomplete: str) -> list[str]:
    """Typer/Click autocompletion callback for date column options with smart ordering."""
    _ = args
    file_path = _ctx_file_path(ctx)
    columns = _get_date_columns(file_path)

    # Determine current position in --x values for smart ordering
    x_values = _ctx_param_values(ctx, "x")
    position = len(x_values)

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
            has_empty = False
            with open(key[0], newline="") as f:
                reader = csv.DictReader(f)
                for i, row in enumerate(reader):
                    if i >= max_rows:
                        break
                    val = row.get(column, "").strip()
                    if not val:
                        has_empty = True
                        continue
                    if val not in seen:
                        seen.add(val)
                        values.append(val)
            if has_empty:
                values.append("(empty)")
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
    """Find the most relevant column from context params for pre-filling.

    Priority: --where (column already being filtered) > --y > --x.
    This lets --where-not inherit the same column as a preceding --where.
    """
    # Check existing --where values first: extract COL from COL=value
    where_vals = _ctx_param_values(ctx, "where")
    for expr in reversed(where_vals):
        if "=" in expr:
            return expr.split("=", 1)[0]

    for param in ("y", "x"):
        vals = _ctx_param_values(ctx, param)
        if vals:
            return vals[-1]
    return None


def complete_where(ctx: click.Context, args: list[str], incomplete: str) -> list[str]:
    """Typer/Click autocompletion callback for --where values.

    Context-aware: pre-fills column name from the last --x/--y.
    """
    _ = args
    file_path = _ctx_file_path(ctx)
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

    # No "=" yet — suggest COL= completions (column name only, no values).
    # Shells strip the common prefix from display, so once the user picks
    # "status=" and the next tab fires, values appear as "open", "closed", …
    # Mixing full "status=open" entries here with bare "region=" entries is
    # confusing; keep stage 1 uniform.
    context_col = _last_context_column(ctx)
    col_map = {c.lower(): c for c in columns}
    actual_context_col = col_map.get(context_col.lower()) if context_col else None

    # Context column first, then remaining columns in CSV order
    ordered: list[str] = []
    if actual_context_col:
        ordered.append(actual_context_col)
    for col in columns:
        if col != actual_context_col:
            ordered.append(col)

    suggestions = [f"{col}=" for col in ordered]

    if incomplete:
        lower = incomplete.lower()
        suggestions = [s for s in suggestions if s.lower().startswith(lower)]

    return suggestions


# ---------------------------------------------------------------------------
# Monkey-patch Typer's bash completion script to handle 'col=value' tokens.
#
# Problem: bash's COMP_WORDBREAKS includes '=' by default, so typing
# '--where status=' causes bash to split 'status=' into two tokens and pass
# an empty string as the current incomplete word to Typer/Click.  This makes
# stage-2 (value list) never trigger.
#
# Fix: reconstruct the word list from COMP_LINE (the raw command line) using
# space-only splitting so 'status=' or 'status=Don' stays as one token.
# After getting completions from Typer (e.g. 'status=Done'), strip the
# 'col=' prefix before populating COMPREPLY so bash inserts just the value
# after the '=' that is already on the command line.
# ---------------------------------------------------------------------------

_BASH_EQ_SAFE = """
%(complete_func)s() {
    local IFS=$'\\n'

    # Re-tokenise from the raw line so 'col=val' is kept as one word.
    local _line="${COMP_LINE:0:$COMP_POINT}"
    local -a _words=()
    IFS=' ' read -ra _words <<< "$_line"
    local _cword=$(( ${#_words[@]} - 1 ))
    [[ "$_line" =~ [[:space:]]$ ]] && { _words+=(""); ((_cword++)); }
    local _cur="${_words[$_cword]:-}"

    # Detect a 'col=' prefix (e.g. 'status=' or 'status=Don').
    local _eq_prefix=""
    [[ "$_cur" == *"="* ]] && _eq_prefix="${_cur%%=*}="

    IFS=$'\\n'
    local -a _completions
    _completions=( $( env COMP_WORDS="${_words[*]}" \\
                          COMP_CWORD=$_cword \\
                          %(autocomplete_var)s=complete_bash $1 ) )

    # Strip the col= prefix from each completion so bash inserts only the
    # value part after the '=' already on the command line.
    # With -o nospace we must manually append a space to "final" completions
    # (those that don't end with '=') so normal word separation works.
    COMPREPLY=()
    for _c in "${_completions[@]}"; do
        local _val="$_c"
        if [[ -n "$_eq_prefix" && "$_c" == "$_eq_prefix"* ]]; then
            _val="${_c#$_eq_prefix}"
        fi
        if [[ "$_val" == *"=" ]]; then
            COMPREPLY+=("$_val")
        else
            COMPREPLY+=("$_val ")
        fi
    done

    return 0
}

complete -o nospace -o default -F %(complete_func)s %(prog_name)s
"""

_typer_completion.COMPLETION_SCRIPT_BASH = _BASH_EQ_SAFE
_typer_completion._completion_scripts["bash"] = _BASH_EQ_SAFE
