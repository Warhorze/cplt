# Plan: Smarter Summarise — Category Threshold, Bar Graphs & Histograms

## Context

The current `summarise` command shows raw frequency lists for all columns, which produces useless output in several cases:
1. **ID-like columns** (e.g. PassengerId, Name) — every value has freq=1, providing no insight
2. **Low-cardinality numerics** (e.g. Survived with 2 values, Pclass with 3) — shown as numeric with freq counts instead of as categorical distributions
3. **High-cardinality numerics** (e.g. Age, Fare) — shown as top-5 freq which hides the distribution shape

The goal is to make summarise output more informative by auto-classifying columns and rendering them appropriately.

## New CLI Option

Add `--category N` (default: 10) to the `summarise` command.
- Columns with `unique_count <= N` are treated as **categorical** regardless of detected type
- This lets users tune the threshold (e.g. `--category 5` for stricter, `--category 20` for looser)

## Behavior Changes

### 1. ID Detection — suppress useless frequencies
Columns where `unique_count == non_null_count` and `unique_count > category_threshold` are **ID-like**.
- In the distribution column: show `(all unique)` instead of freq-1 values

### 2. Categorical Columns — stacked bar graph with percentages
When `unique_count <= category_threshold`:
- Rename "Top Values (freq)" column to "Distribution"
- Show top 5 categories + lump the rest into "other"
- **Visual/Rich format**: two parts in the Distribution cell:
  1. A single **colored stacked bar** (`█` segments, each category a different color, 40 chars wide)
  2. A **vertical legend** below the bar — each line is the category name (colored to match its bar segment) + percentage. No dots/symbols — the text color *is* the legend.
  - Example:
    ```
    ██████████████████████████████████████████
    cat_a  25%
    cat_b  20%
    cat_c  15%
    cat_d  12%
    cat_e  10%
    other  18%
    ```
- **Compact format** (no color, for LLMs): just percentages as text
  - Example: `cat_a 25%, cat_b 20%, cat_c 15%, cat_d 12%, cat_e 10%, other 18%`

### 3. Numeric Histograms — sparkline distribution
When `detected_type == "numeric"` and `unique_count > category_threshold`:
- Show a **sparkline histogram** using the existing `_SPARK_CHARS` (`▁▂▃▄▅▆▇█`) from compact.py
- Bin values into ~20 bins, render as a single sparkline row with min/max labels
- Example (compact):
  ```
  ▁▂▃▅▇█▇▅▃▂▁ 2.0 .. 66.0
  ```
- Reuses the same sparkline approach already used in `compact_line`

### 4. Summary table changes
- Rename "Top Values (freq)" → "Distribution" across all formats
- Show `null_count` instead of `non_null_count` (show what's missing, not what's present)
- Drop the "Rows" column (it's the same for every row, already shown in the header as `rows: N`)

## Files to Modify

| File | Change |
|------|--------|
| `src/cplt/cli.py` (~626-817) | Add `--category` option, pass to summarise, update visual/semantic rendering to use Distribution column |
| `src/cplt/summarise.py` | Add `category_threshold` param, compute `is_id`, `is_categorical`, `histogram_bins` on `ColumnSummary` |
| `src/cplt/compact.py` (~353-492) | Update `compact_summarise` to render stacked bars (categorical) and sparkline histograms (numeric) |
| `tests/test_summarise.py` | Tests for category detection, ID detection, histogram binning |
| `tests/ux/test_summarise_combinations.py` | UX tests for `--category` with other options |

## Implementation Steps (TDD)

1. **test: add failing tests for category threshold and ID detection** — red phase
2. **feat(summarise): add category_threshold, is_id, is_categorical, histogram_bins to ColumnSummary** — green phase
3. **test: add failing tests for stacked bar and sparkline histogram rendering in compact** — red
4. **feat(compact): render categorical stacked bars and numeric sparkline histograms** — green
5. **feat(cli): add --category option and update visual/semantic rendering** — wire it up
6. **test: UX combination tests for --category** — ensure cross-option interactions work
7. **refactor: cleanup** — if needed

## Resolved Questions

1. **Bar graph width**: Fixed width (e.g. 40 chars), consistent with existing `compact_bar` which uses `width=40`
2. **Histogram for dates**: Numerics only for now — date histograms (binned by month/year) can be a follow-up
3. **Visual format**: Replace the "Top Values" column with "Distribution" — same column, smarter content
4. **Data Quality table**: Keep as-is for now — out of scope for this feature

## Verification

1. `uv run pytest` — all tests pass (496 passed)
2. `uv run cplt summarise -f data/titanic.csv --format compact` — verified:
   - PassengerId/Name show as ID (`(all unique)`) ✅
   - Survived/Pclass/Sex/Embarked show percentages ✅
   - Age/Fare show sparkline histograms ✅
3. `uv run cplt summarise -f data/titanic.csv --format compact --category 5` — threshold tuning works ✅
4. `uv run ruff check src/ tests/ && uv run pyright` — clean ✅

## Status: DELIVERED
