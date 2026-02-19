# Option Combination Matrix & Test Redesign Plan

## Context

As csvplot grows more options per command, option interactions create unexpected or under-specified behavior. Tests were added per-feature, not per-combination. This plan documents actual current behavior, proposes a pipeline-stage approach to tame the combinatorial complexity, and defines expected behavior for every option pair.

---

## General Principles

1. **Option order must not matter** — the result should be the same regardless of CLI argument order.
2. **Dead options must be removed** — `--no-encode` and `--no-transpose` add complexity with zero value. Change to simple flags.
3. **No-op combinations must not be silently swallowed** — either make them work or reject with an error.
4. **Reuse options across commands** — e.g. `--label` could rename axes, not just be timeline-specific.
5. **`--top` belongs to `--encode`** — it controls how many encoded columns to show, not a general-purpose row limiter.
6. **Binary encode should use `col=value` format** — same as one-hot. ≤2 unique produces `col=val1` and `col=val2` columns with 1/0, not a passthrough.

---

## Strategy: Pipeline Stages + Stage-Level Contracts

The core problem: N options create N×(N-1)/2 pairs. Bubble has 12 options → 66 pairs. Testing every pair is unsustainable.

Instead, **decompose the pipeline into ordered stages** where each stage has a clear input/output contract:

```
Stage 1: INPUT         --file, --head
Stage 2: FILTER        --where, --where-not
Stage 3: SAMPLE        --sample
Stage 4: TRANSFORM     --encode (with implicit --top for cap)
Stage 5: AGGREGATE     --group-by  OR  per-row matrix
Stage 6: ARRANGE       --sort, --transpose
Stage 7: PRESENT       --color, --format, --title, --label
```

Options within the same stage are independent. Options only affect downstream stages. This reduces tests from 66 pairs to ~20 meaningful cross-stage interactions.

---

## Bubble Command — Full Combination Matrix

Bubble has the most options (12) and the most interaction complexity.

### Processing pipeline (actual code order in `cli.py:856-960` and `bubble.py`)

```
CSV file
  → --head N          (limit raw CSV rows read — bubble.py:154)
  → --where/--where-not  (filter_rows iterator — bubble.py:142-144)
  → --sample N        (random.sample from collected rows — bubble.py:158-159)
  → --encode          (scan unique values from collected rows → expand — bubble.py:162-166)
  → --top N           (rank expanded columns by fill-rate, keep top N — bubble.py:178-186)
  → build matrix      (bubble.py:168-189)
  ──── return BubbleSpec ────
  → --sort            (cli.py:928-935, calls sort_bubble_spec)
  → --transpose       (cli.py:937-940, calls transpose_bubble_spec)
  → --color           (color_keys built during matrix build, used by renderer)
  → --format + --title (render — cli.py:946+)
```

**Separate path for `--group-by`** (cli.py:877-906):
```
CSV file
  → --where/--where-not  (filter_rows — bubble.py:279-282)
  → collect all rows (NO --head, NO --sample in this path)
  → --encode          (scan unique values → expand — bubble.py:298-302)
  → --top N           (rank expanded columns by overall fill-rate — bubble.py:314-322)
  → build grouped counts (bubble.py:305-311)
  ──── return GroupedBubbleSpec ────
  → return early (cli.py:906) — --sort, --transpose, --color NEVER reached
```

### Pairwise Combination Matrix

Legend:
- **Current**: what the code actually does today
- **Suggestion**: what I think it should do (marked with 💡)
- **Test?**: existing test coverage

---

#### `--head` combinations

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--head` + `--where` | Head limits raw CSV rows, then where filters from those limited rows. You might get fewer results than `--head N` suggests. | Parameterized exit-code only |
| `--head` + `--where-not` | Same as above with exclusion | Parameterized exit-code only |
| `--head` + `--encode` | Head limits rows → encode sees cardinality of limited rows only | No |
| `--head` + `--sample` | Head limits rows → sample draws from those | No |
| `--head` + `--group-by` | **`--head` is NOT passed to `load_bubble_grouped`** — it reads ALL rows. `--head` is silently ignored. | No |
| `--head` + `--top` | Head limits rows → top ranks from limited data | No | 
| `--head` + `--sort` | Head limits rows → sort operates on limited result | No |
| `--head` + `--transpose` | Head limits rows → transpose operates on limited result | No |

💡 **Fix needed**: `--head` should be passed to `load_bubble_grouped` too.

💡 **Note**: `--top` is scoped to `--encode` — it controls how many encoded columns to show, not a general row/column limiter for `--head`.

---

#### `--where` / `--where-not` combinations

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--where` + `--where-not` | Both applied via `filter_rows`. Where includes, where-not excludes. Same-column where = OR, cross-column = AND. Where-not is always AND. | No |
| `--where` + `--encode` | Filter first → encode scans only filtered rows → cardinality based on filtered data. If filtering reduces unique values to ≤2, column stays binary instead of one-hot. | Unit: `test_encode_with_where`. No UX test. |
| `--where-not` + `--encode` | Same logic as above but via exclusion | No |
| `--where` + `--group-by` | Filter first → group filtered rows. Some groups may vanish. | UX: `test_group_by_with_where` |
| `--where` + `--top` | Filter first → fill-rates computed on filtered data → top N from those | No |
| `--where` + `--sort` | Filter first → sort filtered rows | No |
| `--where` + `--transpose` | Filter first → transpose filtered matrix | No |
| `--where` + `--sample` | Filter first → sample from filtered rows | No |
| `--where` + `--color` | Filter first → color_keys from filtered rows | No |

---

#### `--encode` combinations

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--encode` + `--top N` | Encode expands columns → top N ranks the expanded columns by fill-rate | Unit: `test_encode_with_top` |
| `--encode` + `--group-by` | Both paths support encode. Encode expands → grouped counts built per expanded column. | UX: `test_encode_with_group_by` |
| `--encode` + `--transpose` | Encode expands → transpose swaps (encoded col names become row labels) | UX: `test_encode_with_transpose` |
| `--encode` + `--sort` | Encode expands columns → sort orders rows by fill across expanded cols | No |
| `--encode` + `--color` | Encode expands columns, color_keys built from separate column. Independent. | No |
| `--encode` + `--sample` | Sample drawn from collected rows → encode scans sampled rows' cardinality. Cardinality based on sample, not full data. | No |
| `--encode` (high cardinality) | >2 unique → one-hot. **No cap.** 100 unique values → 100 columns. Output is unreadable. | No |

💡 **Suggestion**: Auto-cap at 20 encoded columns when `--top` not explicitly set. Print stderr warning: "Encoded N columns, showing top 20. Use --top to adjust." (Decision already confirmed above.)

---

#### `--group-by` combinations

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--group-by` + `--sort` | **`--sort` is silently ignored.** Group-by returns early at cli.py:906 before sort is checked at cli.py:928. | No 
| `--group-by` + `--transpose` | **`--transpose` is silently ignored.** Same reason — early return. | No |
| `--group-by` + `--color` | **`--color` is silently ignored.** `load_bubble_grouped` does not accept `color_col`. | No |
| `--group-by` + `--sample` | **`--sample` is silently ignored.** `load_bubble_grouped` does not accept `sample_n`. | No |
| `--group-by` + `--head` | **`--head` is silently ignored.** `load_bubble_grouped` does not accept `max_rows`. | No |
| `--group-by` + `--top` | Works. Top N applied to grouped column fill-rates. | No |
| `--group-by` + `--where` | Works. Filter before grouping. | UX test exists |
| `--group-by` + `--encode` | Works. Encode expands, grouped counts per expanded column. | UX test exists |

💡 **Suggestions**:
- `--group-by` + `--sort`: Should work — sort groups by overall fill-rate or name.
- `--group-by` + `--transpose`: Could transpose the group table. Or warn as no-op.
- `--group-by` + `--color`: Warn as no-op (grouping replaces per-row identity).
- `--group-by` + `--sample`: Warn as no-op (sample is per-row, grouping aggregates).
- `--group-by` + `--head`: Should be passed through, or warn.

💡 **Valid use case**: `--group-by team --color department` — group rows by team, color groups by department. Should be supported, not ignored.

---

#### `--transpose` combinations

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--transpose` + `--sort` | Sort runs first (cli.py:928), then transpose (cli.py:937). Rows are sorted, THEN swapped to columns. | UX: `test_transpose_with_sort` |
| `--transpose` + `--top` | Top filters columns in `load_bubble_data`, then transpose swaps them to rows. Works. | No |
| `--transpose` + `--color` | `transpose_bubble_spec` sets `color_keys=[]`. Color is silently lost. | No |
| `--transpose` + `--sample` | Sample runs in `load_bubble_data` before transpose in cli.py. Works. | No |

💡 **Suggestion**: `--transpose` + `--color` — warn that color has no effect.

---

#### `--sort` combinations

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--sort` + `--top` | Top filters columns (in loader), sort orders rows (in cli.py). Independent, both work. | No |
| `--sort` + `--color` | Sort reorders rows, color_keys reordered with them (`sort_bubble_spec` preserves color_keys order). Works. | No |
| `--sort` + `--sample` | Sample runs in loader, sort runs after. Works. | No |

---

#### `--sample` combinations

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--sample` + `--top` | Sample rows → build matrix → top ranks columns from sampled data. Works. | No |
| `--sample` + `--color` | Sample rows → color_keys from sampled rows. Works. | No |
| `--sample` + `--encode` | Sample rows → encode scans sampled cardinality. Cardinality may differ from full data. | No |

---

#### `--top` combinations

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--top` + `--color` | Top filters columns, color is per-row. Independent, both work. | No |

---

#### `--color` combinations (remaining)

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--color` + `--format compact` | Color keys are included in compact output. Works. | No explicit test |
| `--color` + `--format semantic` | Color keys are used in semantic output. Works. | No explicit test |

---

#### Key triple+ combinations

| Combination | Current behavior | Test? |
|------------|-----------------|-------|
| `--where` + `--encode` + `--top` | Filter → encode on filtered cardinality → top N of expanded. Works. | No |
| `--encode` + `--group-by` + `--sort` | Encode + group-by works. **Sort silently ignored** (group-by early return). | No |
| `--encode` + `--top` + `--transpose` | Encode → top N → transpose. Works. | No |
| `--where` + `--group-by` + `--encode` | Filter → group filtered → encode expanded. Works. | No |
| `--head` + `--where` + `--encode` | Head limits → filter → encode. Works (but head is pre-filter). | No |
| `--where` + `--encode` + `--group-by` + `--top` | Filter → encode → group → top. Works. | No |
| `--group-by` + `--sort` + `--transpose` | All three silently ignored by group-by early return (sort + transpose never reached). | No |

---

## Timeline Command — Combination Matrix

### Processing pipeline (actual code in `cli.py` + `reader.py`)

```
CSV file
  → --head N            (limit raw rows)
  → --where/--where-not (filter)
  → parse dates, build segments per --x pair (layers)
  → --from/--to         (clip segments to date window)
  → --open-end          (replace null end dates with today)
  → --y + --y-detail    (build y-labels)
  → --color             (color segments by column)
  → --dot               (load dot markers)
  → --vline + --label   (add vertical reference line)
  → --format + --title  (render)
```

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--where` + `--from`/`--to` | Where filters rows, from/to clips segments. Independent, both work. | No |
| `--where` + `--color` | Where filters rows, color applied to remaining. Works. | No |
| `--where` + `--no-open-end` | Where filters rows first, then open-end logic on remaining. Works. | No |
| `--where` + `--y-detail` | Where filters rows, y-detail sub-groups remaining. Works. | No |
| `--where` + `--dot` | Where filters rows, dots loaded from remaining. Works. | No |
| `--color` + `--y-detail` | Color segments by one column, sub-group by another. Both apply. Works. | No |
| `--color` + `--multi-layer` | Each layer gets colored independently. Works visually. | No |
| `--vline` + `--from`/`--to` | Vline rendered regardless of window — if outside window, may not be visible but no error. | No |
| `--dot` + `--from`/`--to` | Dots outside window are clipped by renderer. Works. | No |
| `--from`/`--to` + `--no-open-end` | No-open-end drops null-end rows, from/to clips remaining. Works. | No |
| `--txt` + `--format compact` | Txt is a visual-only flag. Compact ignores it (verified by existing test `test_txt_compact_is_noop`). | UX test exists |
| `--multi-layer` + `--y-detail` | Multiple layers × sub-groups. Both apply independently. | No |
| `--head` + `--where` | Head limits raw rows, then filter. Works. | No |
| `--head` + `--from`/`--to` | Head limits raw rows, from/to clips segments. Works. | No |

---

## Bar Command — Combination Matrix

### Processing pipeline

```
CSV file
  → --head N            (limit raw rows)
  → --where/--where-not (filter)
  → count values of --column
  → --sort              (sort counts)
  → --top N             (keep top N after sort)
  → --horizontal + --labels (visual rendering flags)
  → --format + --title  (render)
```

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--where` + `--sort` | Filter → count filtered → sort counts. Works. | No |
| `--where` + `--top` | Filter → count filtered → top N from filtered counts. Works. | No |
| `--top` + `--sort label` | Top N by count (default sort=value), then if sort=label, sorts top N alphabetically. Actual: `--sort` determines count ordering THEN `--top` takes first N. So `--sort label` + `--top 3` = alphabetical first 3, NOT top 3 by count then sorted. | No |
| `--where` + `--labels` | Filter → count → labels on filtered bars. Visual-only. Works. | No |
| `--horizontal` + `--format compact` | Horizontal is visual-only. Compact ignores it (verified by `test_horizontal_compact_is_noop`). | UX test exists |
| `--labels` + `--format compact` | Labels is visual-only. Compact ignores it. | No |
| `--head` + `--where` | Head limits raw rows, filter from limited. Works. | No |
| `--head` + `--top` | Head limits raw rows → count → top N. Works. | No |

💡 **Suggestion**: `--top` + `--sort`: Current behavior means `--sort label --top 3` gives alphabetically first 3, not highest 3 sorted by name. Consider whether `--top` should always select by count first, then `--sort` reorders the selected set.

---

## Line Command — Combination Matrix

### Processing pipeline

```
CSV file
  → --head N            (limit raw rows)
  → --where/--where-not (filter)
  → parse x values, collect y series
  → --color             (group rows into separate series)
  → --format + --title  (render)
```

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--where` + `--color` | Filter → group filtered rows by color column. Works. | No |
| `--where` + `--multi-y` | Filter → plot multiple y series from filtered. Works. | No |
| `--color` + `--multi-y` | Each y column × each color group = separate series. Works (produces N×M lines). | No |
| `--head` + `--where` | Head limits raw rows, filter from limited. Works. | No |
| `--head` + `--color` | Head limits raw rows, group from limited. Works. | No |

---

## Summarise Command — Combination Matrix

### Processing pipeline

```
CSV file
  → --head N            (limit raw rows)
  → --where/--where-not (filter)
  → compute stats
  → --sample N          (random sample rows)
  → --format            (render)
```

| Pair | Current behavior | Test? |
|------|-----------------|-------|
| `--where` + `--sample` | Filter → sample from filtered rows. Works. | No |
| `--head` + `--where` | Head limits raw rows, filter from limited. Works. | No |
| `--head` + `--sample` | Head limits → sample from limited. Works. | No |
| `--where` + `--where-not` | Both applied. Works. | No |

---

## Summary of Silent No-Ops (options that are accepted but do nothing)

| Command | Combination | What happens |
|---------|------------|-------------|
| bubble | `--group-by` + `--sort` | Sort silently ignored (early return) |
| bubble | `--group-by` + `--transpose` | Transpose silently ignored (early return) |
| bubble | `--group-by` + `--color` | Color silently ignored (not passed to grouped loader) |
| bubble | `--group-by` + `--sample` | Sample silently ignored (not passed to grouped loader) |
| bubble | `--group-by` + `--head` | Head silently ignored (not passed to grouped loader) |
| bubble | `--transpose` + `--color` | Color keys emptied by transpose_bubble_spec |
| bar | `--horizontal` + `--format compact/semantic` | Horizontal silently ignored |
| bar | `--labels` + `--format compact/semantic` | Labels silently ignored |
| timeline | `--txt` + `--format compact/semantic` | Txt silently ignored |

---

## Scale Expectations for `--encode`

| Cardinality | `--encode` behavior | Readability | Action |
|------------|--------------------|-----------|----|
| ≤2 unique | Binary passthrough | Good | OK |
| 3-20 unique | One-hot → 3-20 cols | Good | OK |
| 21+ unique | One-hot would produce >20 cols | Poor/Unusable | Auto-cap: apply `--top 20` to encoded columns + stderr warning. If user passed explicit `--top`, respect their value. |

💡 **Change**: Binary passthrough (≤2 unique) should also use `col=value` format with 1/0 values, same as one-hot. No special "passthrough" behavior — all encoded columns use consistent `col=value` naming.

---

## Architectural Assessment: Current vs Strategy Pattern

### Current architecture

**Bar/Line/Timeline/Summarise**: "God function" pattern — one loader does everything (read, filter, transform, build spec), CLI renders. Works fine — few options, no interacting stages.

**Bubble**: Split brain —
- `load_bubble_data()` handles stages 1-4 in one function with 10 parameters
- `sort_bubble_spec()` / `transpose_bubble_spec()` are separate post-processing functions
- `load_bubble_grouped()` **duplicates ~60% of `load_bubble_data`** but skips head/sample/color and returns `GroupedBubbleSpec` (different type)
- CLI has `if group_by: ... return` that bypasses sort/transpose/color entirely

### Do we need a strategy pattern?

**Bar/Line/Timeline/Summarise: No.** Simple enough as-is.

**Bubble: Yes, but lightweight.** The issue is specifically the AGGREGATE stage — group-by vs per-row is a strategy choice that should produce a compatible output, not fork the entire pipeline.

### Proposed refactor: split bubble into stage functions

```python
# Stages 1-3: shared
def load_bubble_rows(path, cols, y_col, *, max_rows, wheres, where_nots, sample_n) -> list[dict]

# Stage 4: TRANSFORM
def encode_columns(rows, cols, *, encode, top) -> tuple[list[ExpandSpec], list[str]]

# Stage 5: AGGREGATE (the strategy — just two functions behind if/else)
def build_row_matrix(rows, expand_specs, y_col, color_col) -> BubbleSpec
def build_grouped_matrix(rows, expand_specs, group_by) -> BubbleSpec  # same return type!

# Stages 6-7: already exist, no change
sort_bubble_spec(spec, sort)
transpose_bubble_spec(spec)
```

CLI becomes linear — no early return, no code path split:
```python
rows = load_bubble_rows(...)
specs, names = encode_columns(rows, cols, encode=encode, top=top)
spec = build_grouped_matrix(...) if group_by else build_row_matrix(...)
if sort: spec = sort_bubble_spec(spec, sort)
if transpose: spec = transpose_bubble_spec(spec)
render(spec, ...)
```

### GroupedBubbleSpec → extend BubbleSpec

Root cause of the split: two incompatible types. Fix: add optional `cell_values: list[list[str]]` to BubbleSpec. Normal mode = None, grouped mode = percentage strings. Renderers check this field. No new types, no ABC.

---

## Proposed Fixes Summary

### Bubble
| Combination | Current | Proposed |
|------------|---------|----------|
| `--group-by` + `--sort` | Silently ignored | Sort groups by fill-rate or name |
| `--group-by` + `--transpose` | Silently ignored | Transpose the group table |
| `--group-by` + `--color` | Silently ignored | Color groups by a column |
| `--group-by` + `--sample` | Silently ignored | Error: "Cannot sample with --group-by" |
| `--group-by` + `--head` | Silently ignored | Pass through to limit input rows |
| `--transpose` + `--color` | Color lost | Warn: "--color has no effect with --transpose" |
| `--encode` binary | Passthrough as original column | Use `col=value` format with 1/0 |
| `--encode` high cardinality | No cap, unreadable | Auto-cap at 20 + stderr warning |
| `--no-encode` / `--no-transpose` | Dead toggles | Remove, use simple flags |

### Bar
| Combination | Current | Proposed |
|------------|---------|----------|
| `--top` + `--sort label` | Sort first, then take top N | Always select top N by count, then sort selected |

### Refactor: merge group-by into main pipeline

Currently `--group-by` takes a separate code path that returns early. Merge it into the main pipeline so sort/transpose/color/head all work with it.

---

## Implementation Order

1. **Tests for current behavior** — lock in what works before refactoring
2. **Tests for desired behavior** (xfail) — define the spec
3. **Refactor bubble pipeline** — merge group-by, fix encode, add auto-cap
4. **Fix bar --top + --sort ordering**
5. **Remove xfail markers** as tests go green

---

## Test Redesign

### New test files

```
tests/ux/
  conftest.py                    # extend with new fixtures
  test_format_matrix.py          # keep as-is
  test_error_ux.py               # extend with incompatible combo errors
  test_scale_ux.py               # extend with encode scale
  test_options_ux.py             # keep for single-option tests
  test_bubble_combinations.py    # NEW: ~25 pairwise + triple tests
  test_timeline_combinations.py  # NEW: ~10 pairwise tests
  test_bar_combinations.py       # NEW: ~6 pairwise tests
  test_line_combinations.py      # NEW: ~4 pairwise tests
  test_summarise_combinations.py # NEW: ~3 pairwise tests
```

### New fixtures needed

- `bubble_high_cardinality_csv`: 30+ rows, column with 25+ unique values (encode scale test)
- `bubble_medium_cardinality_csv`: 15 rows, column with 8 unique values (encode at manageable scale)

### Priority order

1. Bubble combinations (most options, most user pain)
2. Scale guardrails for encode
3. Timeline combinations
4. Bar combinations
5. Line combinations
6. Summarise combinations

---

## Verification

```bash
uv run pytest tests/ux/test_bubble_combinations.py -v
uv run pytest tests/ux/ -v
uv run ruff check src/ tests/
uv run pytest
```
