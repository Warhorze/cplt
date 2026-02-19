# Bubble Plot — Horizontal Layout & Scalability Plan

## Problem

The current bubble matrix is vertical: rows = entities (y-labels), columns = fields. This layout hits terminal height limits fast — auto-capped at `max(10, terminal_lines - 10)` rows for visual/semantic. With real datasets (hundreds or thousands of entities), showing only 10 rows is nearly useless.

## Goals

1. Support large row counts without arbitrary truncation
2. Provide both per-entity detail and aggregate summary views
3. Keep compact format LLM-friendly and token-efficient

---




## Changes

### 1. Remove auto-cap for visual/semantic

**Problem**: The `auto_max_rows` cap silently hides most rows. Terminals scroll vertically — there's no reason to cap.

**Approach**:
- Remove the `auto_max_rows` logic in `cli.py` that limits visual/semantic bubble output
- Keep `--head N` and `--sample N` as explicit user-controlled limits
- Add a footer line showing total row count when `--head` or `--sample` truncates: `"Showing 50 of 891 rows"`

**Files**: `cli.py`

---

### 2. Transpose mode (`--transpose`)

**Problem**: When there are few columns (3-5) but many rows (100+), the matrix is tall and narrow — wasted horizontal space, hard to scan.

**Approach**:
- Add `--transpose` flag to the `bubble` command
- Swap axes: column names become row labels (left side), entity names become column headers (top)
- Truncate entity names to ~6 chars or use numeric IDs in column headers
- Terminal scrolls vertically through the few field-rows; many entities fit across

**Layout (transposed)**:
```
         | Alice | Bob | Carol | Dave | Eve | ...
Cabin    |   ●   |     |   ●   |  ●   |     |
Age      |   ●   |  ●  |   ●   |  ●   |  ●  |
Embarked |   ●   |  ●  |   ●   |      |  ●  |
```

**When useful**: Few columns, many rows. The CLI can auto-suggest transpose when `len(col_names) < len(y_labels) / 10`. I would go further just do it the condition is met or even bolder, why not make this the default? 

**Files**: `cli.py`, `compact.py`, `bubble.py` (new field on BubbleSpec or transpose in renderer)


---

### 3. Aggregation mode (`--group-by`)

**Problem**: Per-entity detail doesn't scale. Users often want "which columns are most/least complete for each category" not "which columns does row #347 have."

**Approach**:
- Add `--group-by COL` option (reuse `--color` column or accept a separate arg)
- Instead of one row per entity, show one row per unique group value
- Each cell shows **fill-rate percentage** or **count** instead of boolean dot
- Use block characters for visual density: `░` (0-25%), `▒` (25-50%), `▓` (50-75%), `█` (75-100%)

**Layout (grouped)**:
```
              | Cabin | Age  | Embarked
Survived=0   | ░ 12% | ▓ 60%| █ 98%
Survived=1   | ▒ 35% | █ 91%| █ 100%
```

**Compact format**: `Survived=0 | Cabin:12% Age:60% Embarked:98%` — one line per group, very token-efficient.

**Files**: `cli.py`, `bubble.py` (new `load_bubble_grouped()` or extend `load_bubble_data()`), `compact.py`, new model or extend `BubbleSpec` with `matrix_values: list[list[float]]`

**Sugestion** : we now already calculate the percentile, it would be use full to see absolute numbers to compare groups. This will also help identify nulls/na/nan

---

### 4. Sort rows by completeness (`--sort`)

**Problem**: Default CSV row order is arbitrary. Users scanning for data quality want to see the most/least complete rows first.

**Approach**:
- Add `--sort` option with values: `fill` (descending, most complete first), `fill-asc` (ascending, least complete first), `name` (alphabetical by y-label)
- Sort `y_labels`, `matrix`, and `color_keys` together after loading

**Files**: `bubble.py` (sort logic after matrix construction)

---

### 5. Summary footer row

**Problem**: Even with all rows shown, it's hard to get an at-a-glance sense of column completeness.

**Approach**:
- Add a footer row to the matrix showing per-column fill-rate
- Visual/semantic: `TOTAL | ▓ 67% | █ 95% | █ 100%`
- Compact: append `fill: Cabin:67% | Age:95% | Embarked:100%`
- Always shown (not gated by a flag)

**Files**: `cli.py` (visual/semantic rendering), `compact.py`, `bubble.py` (compute fill rates)

**Suggestion** : when we'd add `--sort` , `--group-by` and tranpose we'd be able to provide a sample analysis where we can use `--where` and `--where-not`to filter down specific intersting groups 

---

### 6. Column-summary compact mode

**Problem**: For LLM consumption with many rows, even compact format produces too many tokens. Often the LLM only needs aggregate stats.

**Approach**:
- When compact format + `--group-by` is used, emit a dense column-major summary:
  ```
  [COMPACT:bubble] titanic (891 rows, 3 cols)
  group: Survived
  Cabin   | 0:12% 1:35% | overall:20%
  Age     | 0:60% 1:91% | overall:71%
  Embarked| 0:98% 1:100%| overall:99%
  ```
- Without `--group-by`, just emit per-column fill rates (single-line summary)

**Files**: `compact.py`

---

## Implementation Order

| # | Change | Size | Dependencies |
|---|--------|------|--------------|
| 1 | Remove auto-cap | Small | None |
| 2 | Sort by completeness | Small | None |
| 3 | Summary footer row | Small | None |
| 4 | Aggregation mode | Medium | New data path in bubble.py |
| 5 | Column-summary compact | Small | #4 (uses grouped data) |
| 6 | Transpose mode | Medium | None (independent) |

Steps 1-3 are quick wins that can land first. Step 4 (aggregation) is the highest-leverage feature. Step 6 (transpose) is independent and can be built in parallel.

---

## Out of Scope (for now)

- Continuous bubble sizing (`--z` with scaled dot sizes) — different feature entirely
- Interactive pagination / scrolling — terminals handle this natively
- Sparkline rendering within cells — Rich doesn't support inline sparklines cleanly
- Heatmap with numeric values per cell (non-grouped) — aggregation covers the main use case
