# UX Testing Pipeline

> A structured approach to end-to-end testing of CLI output across all commands and formats.

---

## CLI Path Map

Every invocation follows: `csvplot <command> -f <file> <required args> [optional args] --format <fmt>`

Below is the full branching tree. **Bold** = required, `[brackets]` = optional, `{a|b}` = choice.

```
csvplot
├── timeline -f FILE
│   ├── --x COL --x COL                          ← required, must be even count (pairs)
│   │   └── [--x COL --x COL ...]                ← additional layers (layer 1, 2, ...)
│   ├── --y COL                                   ← required (at least 1)
│   │   └── [--y COL ...]                         ← combine into composite label "A | B"
│   ├── [--color COL]                             ← color segments by column value
│   ├── [--txt COL]                               ← label segments (visual only)
│   ├── [--y-detail COL]                          ← sub-group within --y
│   ├── [--marker DATE]                           ← vertical marker line
│   │   └── [--marker-label TEXT]                 ← label for marker (requires --marker)
│   ├── [--open-end / --no-open-end]              ← null end → today (default: on)
│   ├── [--from DATE] [--to DATE]                 ← zoom into date range
│   ├── [--head N]                                ← limit input rows
│   ├── [--where COL=VAL ...] [--where-not ...]   ← filter rows
│   ├── [--title TEXT]                            ← chart title
│   └── [--format {visual|compact|semantic}]      ← output mode (default: visual)
│
├── bar -f FILE
│   ├── --column COL / -c COL                     ← required
│   ├── [--sort {value|label|none}]               ← sort order (default: value)
│   ├── [--horizontal]                            ← horizontal bars (visual only)
│   ├── [--top N]                                 ← show only top N categories
│   ├── [--head N]
│   ├── [--where COL=VAL ...] [--where-not ...]
│   ├── [--title TEXT]
│   └── [--format {visual|compact|semantic}]
│
├── line -f FILE
│   ├── --x COL                                   ← required (single x-axis column)
│   ├── --y COL                                   ← required (at least 1)
│   │   └── [--y COL ...]                         ← multiple series on same chart
│   ├── [--color COL]                             ← split into grouped lines
│   ├── [--head N]
│   ├── [--where COL=VAL ...] [--where-not ...]
│   ├── [--title TEXT]
│   └── [--format {visual|compact|semantic}]
│
├── bubble -f FILE
│   ├── --cols COL                                ← required (at least 1)
│   │   └── [--cols COL ...]                      ← additional matrix columns
│   ├── --y COL                                   ← required (row label column)
│   ├── [--color COL]                             ← color rows by column
│   ├── [--top N]                                 ← top N columns by fill-rate
│   ├── [--head N]
│   ├── [--where COL=VAL ...] [--where-not ...]
│   ├── [--title TEXT]
│   └── [--format {visual|compact|semantic}]
│
└── summarise -f FILE
    ├── [--head N]
    ├── [--sample N]                              ← show N random rows below summary
    ├── [--where COL=VAL ...] [--where-not ...]
    └── [--format {visual|compact|semantic}]
```

### Shared options (all commands)

| Option | Type | Default | Notes |
|--------|------|---------|-------|
| `-f` / `--file` | PATH | required | must exist, must be file |
| `--head` | int | none | limit CSV rows read |
| `--where` | COL=VAL | none | repeatable, same-col = OR, cross-col = AND |
| `--where-not` | COL=VAL | none | repeatable, exclude matching rows |
| `--format` | choice | `visual` | `visual` / `compact` / `semantic` |
| `--title` | str | filename | not on `summarise` |

### Option interactions and constraints

```
--marker-label ──requires──▶ --marker
--txt ──────────only affects──▶ --format visual
--horizontal ───only affects──▶ --format visual
--open-end ─────only affects──▶ timeline
--sample ───────only affects──▶ summarise
--y-detail ─────only affects──▶ timeline
--top ──────────only on──▶ bar, bubble (different semantics)
--color ────────on──▶ timeline (segment color), line (group-by), bubble (row color)
--x ────────────on──▶ timeline (date pairs, even count), line (single column)
--y ────────────on──▶ timeline (list, composite), line (list, multi-series), bubble (single, label)
```

### Test path coverage target

Each branch in the tree above maps to at least one UX test. The matrix:

```
                          timeline  bar  line  bubble  summarise
required-args-only            ✓      ✓     ✓      ✓       ✓
+ --format compact            ✓      ✓     ✓      ✓       ✓
+ --format semantic           ✓      ✓     ✓      ✓       ✓
+ --head                      ✓      ✓     ✓      ✓       ✓
+ --where                     ✓      ✓     ✓      ✓       ✓
+ --where-not                 ✓      ✓     ✓      ✓       ✓
+ --color                     ✓      -     ✓      ✓       -
+ --title                     ✓      ✓     ✓      ✓       -
+ --txt                       ✓      -     -      -       -
+ --marker + --marker-label   ✓      -     -      -       -
+ --open-end / --no-open-end  ✓      -     -      -       -
+ --y-detail                  ✓      -     -      -       -
+ --from / --to               ✓      -     -      -       -
+ --sort                      -      ✓     -      -       -
+ --horizontal                -      ✓     -      -       -
+ --top                       -      ✓     -      ✓       -
+ --sample                    -      -     -      -       ✓
+ multi --y                   ✓      -     ✓      -       -
+ multi --x layers            ✓      -     -      -       -
+ multi --cols                -      -     -      ✓       -
error: missing required args  ✓      ✓     ✓      ✓       -
error: invalid --format       ✓      ✓     ✓      ✓       ✓
error: odd --x count          ✓      -     -      -       -
error: unknown column         ✓      ✓     ✓      ✓       -
error: bad --where syntax     ✓      ✓     ✓      ✓       ✓
```

---

## Gap Analysis

Existing test coverage and what's missing:

| Layer | Covered by | Gap |
|-------|-----------|-----|
| Unit: CSV loading, filtering, models | `test_reader.py`, `test_filter.py`, `test_models.py`, `test_bubble.py` | None |
| Unit: compact output contracts | `test_compact.py` (485 lines, all 5 commands) | None |
| Unit: semantic output contracts | `test_semantic.py` | None |
| Unit: autocomplete | `test_completions.py`, `test_completions_where.py` | None |
| Integration: format validation | `test_cli.py` (rejects invalid `--format` for all commands) | None |
| **End-to-end: command x format matrix** | **Not covered** | 5 commands x 3 formats = 15 happy paths untested |
| **End-to-end: option-specific behavior** | **Not covered** | Each optional flag's effect on output untested via CLI |
| **Error UX: actionable messages** | **Partially** — validation exists but error quality (listing columns, readable CSV errors) untested | See github-issues B8, U5 |
| **Scale: large data** | **Not covered** | No tests for 2K+ row behavior |

The UX test suite fills the three bolded gaps.

---

## Test Suite: `tests/ux/`

```
tests/ux/
  __init__.py
  conftest.py            # fixtures: CSV generators, invoke helper
  test_format_matrix.py  # 5 commands x 3 formats = 15 parameterized cases
  test_options_ux.py     # per-command option behavior tests
  test_error_ux.py       # error message quality
  test_scale_ux.py       # large data behavior
```

### Fixtures (`conftest.py`)

One CSV generator per command, each producing a small (10–15 row) file that exercises the command's key paths.

| Fixture | Columns | Rows | Key properties |
|---------|---------|------|----------------|
| `timeline_csv` | `name, start, end, category, detail, label` | 10 | 2 rows share same `name` (tests sub-rows), 1 null end (tests `--open-end`), 3 distinct categories (tests `--color`) |
| `bar_csv` | `status, assignee, priority` | 12 | 4 distinct statuses, uneven counts (tests sorting), 2 assignees (tests `--where`) |
| `line_csv` | `date, temp, humidity, region` | 12 | 2 regions x 6 dates (tests `--color` grouping), monotonic dates (tests x-axis) |
| `bubble_csv` | `name, feat_a, feat_b, feat_c, category` | 10 | Mix of truthy/falsy values, 2 categories (tests `--color`), 1 all-empty row |
| `summarise_csv` | `id, name, score, created, notes` | 15 | Numeric col, date col, text col, 3 nulls, high-cardinality `id` |

Plus a `ux_csvs` dict fixture that returns all five, keyed by command name, for the parameterized format matrix.

### 1. Format Matrix (`test_format_matrix.py`)

Parameterized: 5 commands x 3 formats = 15 test cases.

Per case, assert:
- `exit_code == 0`
- `stdout` is non-empty
- No Python tracebacks in output (`"Traceback" not in stdout`)

This catches regressions where a renderer breaks for a specific format. Existing `test_cli.py` only validates format *rejection* — this tests format *acceptance*.

### 2. Option Behavior (`test_options_ux.py`)

One test per row in the coverage matrix that isn't already covered by unit tests. All assertions use `--format compact` output (stable, machine-readable).

Key tests that exercise non-obvious behavior:

| Test | What it validates |
|------|-------------------|
| `test_timeline_multi_layer` | 2 `--x` pairs produce 2 distinct layer characters in compact output |
| `test_timeline_marker` | `--marker 2024-03-15 --marker-label deadline` appears in output |
| `test_timeline_view_window` | `--from` / `--to` clips segments outside the window |
| `test_timeline_y_detail` | `--y-detail` creates sub-grouped labels |
| `test_timeline_no_open_end` | `--no-open-end` excludes rows with null end dates |
| `test_bar_sort_label` | `--sort label` produces alphabetical order |
| `test_bar_top` | `--top 2` shows only the 2 highest-count categories |
| `test_bar_horizontal` | `--horizontal` with `--format visual` exits 0 (visual-only flag) |
| `test_line_multi_y` | 2 `--y` columns produce 2 sparkline rows in compact |
| `test_line_color_grouping` | `--color region` splits series by group |
| `test_bubble_color_legend` | `--color category` produces a "Legend" section in output |
| `test_bubble_top_fill_rate` | `--top 2` selects the 2 most-filled columns |
| `test_summarise_sample` | `--sample 3` produces a "Sample" section with 3 rows |
| `test_head_limits_all_commands` | `--head 3` on each command, assert row count <= 3 in output |
| `test_where_filters_output` | `--where category=A` on each command, assert only A rows in output |

### 3. Error Message Quality (`test_error_ux.py`)

Tests for existing error paths (regression guards):

| Test | Asserts |
|------|---------|
| `test_odd_x_count` | Error mentions "pairs" or "even" |
| `test_missing_y` | Error mentions "--y" |
| `test_missing_cols_bubble` | Error mentions "--cols" |
| `test_bad_where_syntax` | Error mentions "Expected format" |

Tests for error quality improvements (blocked by github-issues B8, U5 — write as `xfail` until implemented):

| Test | Asserts | Blocked by |
|------|---------|------------|
| `test_unknown_column_lists_available` | Error includes "Available:" with valid column names | U5 |
| `test_malformed_csv_no_traceback` | Error is human-readable, no `TypeError` leak | B8 |

### 4. Scale (`test_scale_ux.py`)

| Test | Data | Asserts |
|------|------|---------|
| `test_bubble_2k_rows` | 2000 rows, 3 cols | `exit_code == 0` with `--format compact` |
| `test_summarise_10k_rows` | 10000 rows, 3 cols | `exit_code == 0`, correct row count in output |
| `test_timeline_500_rows` | 500 rows, 1 layer | `exit_code == 0` with `--format compact` |
| `test_bar_5k_rows` | 5000 rows, 50 distinct values | `exit_code == 0` |

These generate CSVs programmatically in `tmp_path`. No assertion on output content beyond exit code — the goal is "doesn't crash or hang."

---

## Golden Snapshot Tests (deferred)

**Not included in initial implementation.** Compact output format is still evolving (github-issues Phase 1 will change output). Adding golden files now means every bug fix breaks snapshots. Revisit after Phase 1 bug fixes stabilize output.

When ready, add `tests/ux/golden/` with one `.txt` file per command's compact output, generated from the fixture CSVs.

---

## Implementation Order

1. Create `tests/ux/` with `conftest.py` and fixture CSVs (schemas defined above)
2. Format matrix tests (15 parameterized cases)
3. Option behavior tests (coverage matrix rows)
4. Error message tests (existing paths first, `xfail` for B8/U5)
5. Scale tests

---

## Maintenance Rules

- Every bug fix that changes CLI output gets a UX test reproducing the original issue
- Every new command option gets a row in the coverage matrix and a test in `test_options_ux.py`
- UX tests use `--format compact` for content assertions, `visual`/`semantic` only for exit-code checks
