# csvplot — Feature Plan

Constraint: datasets up to 100,000 rows max.

> Note: This is a roadmap document. Some items below describe proposed behavior, not guaranteed current behavior.

---

## 1. Filter (`--where` / `--where-not`)

**Goal:** Filter CSV rows before plotting, with context-aware autocomplete on column values.

**Syntax:**
```bash
# Explicit column: COL=val
csvplot timeline -f data.csv --x S --x E --y name --where "status=open"

# OR within same column: repeat --where with same column
csvplot timeline -f data.csv --x S --x E --y name --where "status=open" --where "status=closed"

# Exclude rows
csvplot timeline -f data.csv --x S --x E --y name --where-not "status=closed"

# AND across different columns
csvplot timeline -f data.csv --x S --x E --y name --where "status=open" --where "region=north"
```

**Semantics:**
- `--where COL=val` — string equality, **case-insensitive by default**
- Same column repeated = **OR** (match any), different columns = **AND** (match all)
- No comma-delimited multi-value syntax — avoids ambiguity when values contain commas
- Optional future `--case-sensitive` flag to opt into exact matching when needed
- `--head` stays as-is for row slicing (limit how many CSV rows are read)

**Autocomplete UX — context-aware pre-fill:**

The autocomplete callback inspects existing args to find the last `--x`/`--y` column and **pre-fills the column name** in suggestions. So the user types:
```bash
csvplot timeline -f data.csv --x status --where <TAB>
# Suggestions: status=open, status=closed, status=pending, ...
```
The user doesn't type the column name — autocomplete fills it from the preceding `--x`. The actual argument is still explicit `COL=val`, so parsing stays simple and scripts remain readable. Without autocomplete, users type the full `COL=val` themselves.

**Implementation:**
- Add a `filter_rows(reader: csv.DictReader, wheres, where_nots) -> Iterator[dict]` generator in `reader.py` that wraps the CSV iterator — all three loaders (`load_segments`, `load_bar_data`, `load_line_data`) get filtering for free
- Available on all commands: timeline, bar, line, summarise, bubble

**Error handling:**
- `--where "nonexistent_col=foo"` → hard error listing valid column names
- `--where "bad_syntax"` (no `=`) → hard error with expected format

**Why string equality only:** Covers ~90% of filtering use cases. Numeric comparisons (>, <, >=) add parser complexity disproportionate to the value — defer until real user demand.

**Key tests:**
- `filter_rows` with single where returns matching subset
- Same column repeated acts as OR
- Different columns act as AND
- Case-insensitive by default, case-sensitive flag works
- Unknown column raises error with helpful message

---

## 2. Summarise (`csvplot summarise`)

**Goal:** Print a pandas-like summary of a CSV file — column types, counts, nulls, unique values, top values.

**Syntax:**
```bash
csvplot summarise -f data.csv
csvplot summarise -f data.csv --where "status=open"
csvplot summarise -f data.csv --head 1000 --sample 5
```

**`--head N` vs `--sample N`:**
- `--head N` — take the **first N rows** from the CSV before any processing. Input limiter, deterministic, fast. Same behavior as all other commands.
- `--sample N` — show N **random rows** as a preview table below the summary. Output-only, does not affect summary stats. Random is more useful than first-N because sorted data often has identical-looking top rows — random gives a real feel for data variety.

**Approach:**
- New `summarise` subcommand
- Composable with `--where` / `--where-not` filters
- Use Rich table for terminal output
- No pandas — single-pass with `collections.Counter` and basic math

**Output per column:**
- Name, detected type (date / numeric / text), row count, non-null count, unique count
- Min / max (for numeric and date columns)
- Top 5 most common values with counts

**Type detection heuristic:** Check all rows during the single pass (not just 10-row sample). A column is "numeric" if >80% of non-null values parse as float. A column is "date" if >80% of non-null values parse via `parse_datetime()`. Otherwise "text".

**High-cardinality guard:** Cap `Counter` at 10K distinct values per column. If a column exceeds this (e.g. UUIDs), stop tracking individual values and report "many unique values (>10K)" instead of top-5. This keeps memory bounded at ~100K rows.

**Error handling:**
- Empty CSV (headers only) → show column names with zero counts, no error
- `--sample N` where N > row count → show all rows, no error

**Key tests:**
- Mixed-type column detected correctly (95% numeric + 5% "N/A" = numeric)
- High-cardinality column caps at 10K and reports correctly
- `--sample` shows random rows as separate table, doesn't affect stats
- Composes with `--where` filters

---

## 3. Bubble Matrix Plot (`csvplot bubble`)

**Goal:** Show presence/absence of values as a dot matrix. Good for feature flags, booleans, and spotting NA/null patterns.

**Syntax:**
```bash
# Binary matrix: dot = value present, empty = missing/falsy
csvplot bubble -f data.csv --cols col1 --cols col2 --cols col3 --y name_col

# With color
csvplot bubble -f data.csv --cols col1 --cols col2 --y name_col --color category
```

**Note on `--cols` vs `--x`:** Uses `--cols` instead of `--x` because the semantics are different from other commands. In `timeline`, `--x` means date column pairs. In `line`, `--x` means a single x-axis column. Using `--cols` avoids overloading `--x` with a third meaning.

**How it works:**
- `--y` is the label column (row identifiers on the y-axis)
- `--cols col1 --cols col2 ...` are the columns to check — column names become x-axis labels
- Each cell shows: `●` = value present, empty = missing/null/falsy
- Falsy = empty string, "0", "false", "no", "null", "none", "na", "nan" (case-insensitive)

**Rendering approach:** Use Rich tables with Unicode dots (`●`/blank) instead of plotext. plotext lacks native dot-matrix/heatmap support — forcing it through scatter plots would look hacky. Rich tables give precise cell control and clean terminal output. **Prototype rendering first** before building the full data pipeline.

**Scaling / truncation:**
- Rows: `--head N` limits row count (same as other commands)
- Columns: `--top N` limits to the N columns with highest fill-rate (most non-falsy values), useful when checking many columns

**Use cases:**
- Feature flag audit: which users have which flags enabled
- Data quality: which columns have missing values per row
- Boolean survey data: which respondents checked which options

**Error handling:**
- Zero columns specified → hard error
- Column not found → hard error listing valid columns

**Key tests:**
- Falsy values correctly detected (all variants)
- `--top N` selects columns by fill-rate
- Rich table output contains expected `●` markers
- Composes with `--where` filters

**Future enhancements (out of scope for v1):**
- `--z` column for bubble size (continuous values)
- `--one-hot` flag to auto-pivot a single column into binary columns
- Color mapping by cell value

### Command Naming Decision (2026-02-15)

- Keep `--cols` as the **primary** bubble option because it is more explicit for matrix-style input.
- Keep `--x` for `timeline` and `line` only.
- Keep `--column` for `bar`.
- Do **not** consolidate bubble onto `--x` as the primary name in the near term.
- Optional future compatibility path: add `--x` as a bubble alias only if requested, while keeping docs centered on `--cols`.

---

## 4. Smarter Autocomplete

**Goal:** Context-aware completions for column names and `--where` values.

**Column completion changes:**
- `--file` completion: only suggest `.csv` files
- `--y` completion: show all columns (users may want numeric y-labels)
- `--color` completion: show all columns
- `line --y` completion: prioritize numeric columns (show first, don't hide others)

**Value completion for `--where`:**

Context-aware: the callback inspects preceding args to find the last `--x`/`--y` column, then pre-fills `COL=` and suggests matching values from that column.

```bash
# User types: csvplot timeline -f data.csv --x status --where <TAB>
# Suggestions: status=open, status=closed, status=pending
#
# User types: --where status=op<TAB>
# Suggestions: status=open, status=option
```

**Matching strategy — keep it simple, no external deps:**
1. **Prefix match first** (`startswith`) — covers the common case where the user is typing from the start
2. **Substring match fallback** (`in`) — catches mid-word matches
3. **Typo tolerance if needed:** `difflib.get_close_matches()` from stdlib — one line of code, zero dependencies, good enough for a few hundred distinct values

No fuzzywuzzy/rapidfuzz needed. The bottleneck for autocomplete UX is latency, not match quality — and string operations on a few hundred values are instant.

**Data source:** Sample first 1000 rows to collect distinct values per column (fast, <50ms).

**Cache strategy:** Cache sampled values alongside existing header cache in `completions.py` keyed by `(path, mtime, column_name)`.

**Error handling:**
- Missing/unreadable CSV file → no completions, no crash
- Malformed CSV → no completions, no crash

**Key tests:**
- Prefix matching returns startswith hits first
- Substring fallback works when prefix misses
- `difflib` catches typos ("opne" → "open")
- Cache invalidates on file mtime change
- Completions don't crash on missing/malformed files

---

## Priority Order

| # | Feature | Size | Rationale |
|---|---------|------|-----------|
| 1 | Filter | Medium | Foundation — unlocks everything else |
| 2 | Summarise | Medium | High standalone value, composes with filter |
| 3 | Bubble matrix | Large | New visualization, high user value |
| 4 | Autocomplete polish | Small | Incremental UX, can land piecemeal alongside other features |

---

## Out of Scope (for now)

- Continuous bubble sizing (`--z` with scaled dot sizes)
- One-hot encoding pivot
- Inline histograms in summarise
- Numeric comparisons in filter (>, <, >=) — string equality covers ~90% of cases
- `--limit` for x-axis value range limiting (separate from `--head` row limiting)
