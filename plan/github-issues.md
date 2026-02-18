# GitHub Issues Action Plan

> Derived from GitHub Issue #1 (Bugs) and Issue #2 (Feedback) — 2026-02-18

---

## Priority 1: Bugs (Issue #1)

These are broken behaviors that need fixing before any new features.

### ~~B1.~~ Moved to F12 — Bubble composite `--y` labels

**Not a bug.** Bubble `--y` is declared as a single `str` in `cli.py:659`, not a `list[str]`. It intentionally accepts one column (the row label). The reporter expected multiple `--y` values to create composite labels like timeline does (`A | B`). This is a feature request — see F12 in Priority 3.

### ~~B2.~~ Completed (2026-02-18) — Large files (2000+ rows) overflow terminal

**Problem:** Terminal fills with values, column names scroll off-screen, many values are missing.
**Root cause:** No automatic pagination or truncation for large datasets in visual mode. Bubble/summarise tables grow unbounded.
**Fix:** Auto-detect terminal height and truncate with a `"... N more rows"` footer. Or apply a default `--head` cap for visual output (e.g. 50 rows for bubble).
**Files:** `src/csvplot/bubble.py`, `src/csvplot/cli.py`
**Test:** Invoke bubble with 200-row CSV without `--head`, assert output includes truncation notice.
**Status:** Implemented via auto terminal-height row cap for bubble visual/semantic output + `"... N more rows"` notice when truncated. (`9d59cf8`)

**User suggestion — transposed bubble axis:**
Rotate the bubble matrix so CSV rows run along the x-axis and checked columns run along the y-axis. This gives more horizontal space for long row labels. Additionally, a fill-rate sparkline could be rendered as a header row showing the % of non-falsy values per column — useful for data quality inspection at a glance. Implementation:
- Add `--transpose` flag (default off, keeps current orientation)
- When transposed: columns become y-labels (short), row labels become x-axis (more room to scroll)
- Optional fill-rate line plot on top showing column completeness
- This is additive — the truncation fix should land first regardless of orientation

### ~~B3.~~ Completed (2026-02-18) — Bubble always shows row numbers (unexpected)

**Problem:** Row number prefixes (`1. Alice`, `2. Bob`) always appear in bubble output, not just with `--head`. The reporter expected plain labels without numbering.
**Root cause:** `cli.py:809` unconditionally formats labels as `f"{row_num:>2}. {shown_label}"`. The numbering exists to cross-reference the label map table shown when labels are truncated, but it's confusing when no truncation occurs.
**Fix:** Only show row numbers when at least one label is truncated (i.e. when `truncated_rows` will be non-empty). This requires a two-pass approach: first determine which labels truncate, then format all labels accordingly.
**Files:** `src/csvplot/cli.py` (lines 798–827)
**Test:** Invoke bubble with short labels and no truncation, assert no `"1. "` prefix in output. Invoke with long labels that trigger truncation, assert row numbers appear.
**Status:** Implemented with two-pass label formatting; numbering now appears only when any row label truncates. (`c9f0349`)

### ~~B4.~~ Completed (2026-02-18) — `--sample` not supported on bubble

**Problem:** `--sample N` works on `summarise` but errors or is ignored on `bubble`.
**Fix:** Wire `--sample` option through to bubble command (show N random rows).
**Files:** `src/csvplot/cli.py`, `src/csvplot/bubble.py`
**Test:** Invoke bubble with `--sample 3`, assert 3 rows rendered.
**Status:** Implemented `bubble --sample N` with random row sampling. (`9d59cf8`)

### ~~B5.~~ Completed (2026-02-18) — Autocomplete fails from different working directory

**Problem:** `csvplot timeline --file ~/Projects/csvplot/data/timeplot2.csv --x <TAB>` fails when run from a different directory.
**Root cause:** Two issues in `completions.py:43-46`:
1. `Path(file_path)` does not call `.expanduser()`, so tilde paths (`~/...`) are not resolved and `.is_file()` returns `False`
2. Even without tilde, relative paths resolve against cwd which may differ from the file's actual location
**Fix:** Add `.expanduser()` before `.resolve()` in `_cache_key()`:
```python
path = Path(file_path).expanduser()
```
**Files:** `src/csvplot/completions.py` (line 44)
**Test:** Mock a completion request with `~/path/to/file.csv` while cwd differs, assert columns returned. Also test with absolute path from different cwd.
**Status:** Implemented path expansion and resolved-path reads for cached completion lookups. (`be2f253`)

### ~~B6.~~ Completed (2026-02-18) — Timeline: duplicate y-label rows drop subsequent `--txt` values

**Problem:** When multiple CSV rows share the same composite `--y` label but have different `--txt` values, only the first txt value appears in the y-tick label. The reporter saw `776-286840-KD0321 | 2102804 | 2006 | 120290146` but the second article `117987179` was silently dropped.
**Root cause:** `renderer.py:131` uses `if key not in txt_by_sub_row` — it keeps only the **first** txt value per `(y_label, sub_row)` key, discarding all subsequent ones.
**Fix:** When multiple txt values exist for the same sub-row, either:
- (a) Append all unique values: `"120290146, 117987179"`, or
- (b) Ensure each row gets its own sub-row so txt values never collide (preferred — aligns with B7)
**Files:** `src/csvplot/renderer.py` (lines 128–132)
**Test:** 3-row CSV where 2 rows share the same `--y` value but have distinct `--txt` values. Assert all txt values appear in output.
**Status:** Implemented unique aggregation of txt values per `(y_label, sub_row)` and join output with commas. (`5918682`)

### ~~B7.~~ Completed (2026-02-18) — Timeline: multi-layer offset makes rows appear doubled

**Problem:** Each row appears to take two visual lines in the timeline, making it hard to match labels to bars.
**Root cause:** This is not a sub-row bug — `_assign_sub_rows` correctly gives each CSV row its own line. The doubling comes from **multi-layer rendering**: when using 2 `--x` pairs, each row gets a primary bar (layer 0) plus a secondary bar (layer 1) offset by `_LAYER_OFFSET = 0.45`. With `_SUB_ROW_HEIGHT = 1.0`, the two layers visually look like two separate rows rather than overlaid ranges for the same entity.
**Fix — UX tuning, not a logic fix:**
- Reduce `_LAYER_OFFSET` (e.g. `0.20`) so layers overlay more tightly
- Use more visually distinct markers per layer (current: `hd`, `braille`, `dot`, `sd`) — consider using color intensity or line thickness instead of vertical offset
- Add a brief legend note explaining what each layer style represents
- For single-layer timelines, confirm no offset is applied (already the case)
**Files:** `src/csvplot/renderer.py` (constants at lines 34–36, rendering at lines 200–231)
**Test:** Two-layer timeline with 3 rows, assert exactly 3 y-tick labels (not 6). Single-layer timeline with 3 rows, assert exactly 3 y-tick labels.
**Status:** Reduced `_LAYER_OFFSET` from `0.45` to `0.20` and improved layer marker differentiation. (`5918682`)

### ~~B8.~~ Completed (2026-02-18) — Malformed CSV error message is unclear

**Problem:** Error `"sequence item 1: expected str instance, NoneType found"` is unhelpful.
**Fix:** Catch `TypeError` in CSV reading and re-raise with `"Failed to read CSV: row N has missing columns. Check file format."`.
**Files:** `src/csvplot/reader.py`
**Test:** Feed a CSV with missing columns, assert error message is human-readable.
**Status:** Added row-shape validation and clear `Failed to read CSV: row N has missing columns...` errors. (`d5e723e`)

### ~~B9.~~ Completed (2026-02-18) — Timeline `--color` unclear which bar belongs to which layer

**Problem:** With multiple `--x` layer pairs, the user can't tell which plotted bar corresponds to which layer. The legend already includes layer names (`renderer.py:257-266`), but the bars themselves look too similar.
**Root cause:** Layer distinction relies on marker style (`hd`, `braille`, `dot`, `sd`) which are subtle in practice. The legend lists layers but the user can't visually map legend entries to bars on the plot.
**Fix:** Combine with B7 tuning — make each layer's visual style more distinct. Options:
- Use different color saturation per layer (e.g. layer 0 = full color, layer 1 = dimmed/lighter)
- Add layer index to `--txt` labels when multiple layers are active
- Render a per-layer sub-legend with the marker style shown inline
**Files:** `src/csvplot/renderer.py` (lines 198, 200–231, 256–280)
**Test:** Two-layer timeline with `--color`, assert legend references layer names. Visually verify with `--format compact` that layers are distinguishable.
**Status:** Legend now includes per-layer marker style hints (`marker=...`) and layer marker styles are more distinct. (`5918682`)

---

## Priority 1: Code Review Feedback (2026-02-18)

### B5 — completions.py

**Overall: Clean fix, good test coverage.**

- `.expanduser()` added in `_cache_key()` and the resolved path (`key[0]`) is correctly propagated to all read calls (lines 58, 73, 135).
- Test `test_tilde_path_is_resolved()` monkeypatches `HOME` and validates column completion end-to-end.
- No gaps identified.

### B8 — reader.py

**Overall: Good pattern, incomplete test coverage.**

- `_ensure_well_formed_row()` is a clean centralised validator. Applied to `load_segments()`, `load_bar_data()`, and `load_line_data()`.
- **Gap:** Only `load_segments()` has a unit test for malformed CSV. `load_bar_data()` and `load_line_data()` have no test exercising the new error path. Add two tests mirroring `test_malformed_csv_raises_clear_error()`.
- **Minor:** The check catches `None` values (too-few columns) but not extra columns (too-many columns, which `csv.DictReader` handles silently by discarding extras). This is acceptable behaviour but worth a comment.

### B2 + B4 — bubble.py + cli.py

**Overall: Well implemented, one UX edge case to document.**

- `total_rows` tracking and `random.sample()` usage are correct.
- Auto-truncation correctly skips when `--head`/`--sample` is explicitly provided.
- **UX edge case (document, not necessarily fix):** When `--sample N` is used without `--head`, `auto_max_rows` is computed first, and `--sample` operates on that already-truncated pool. A user requesting `--sample 200` on a 1000-row file with a 50-line terminal will only receive up to `auto_max_rows` (≈40) rows, not 200. This is intentional (don't overflow terminal) but unintuitive. Add a comment in `cli.py` near line 746 explaining the precedence, and consider emitting a warning like `"--sample 200 reduced to N due to terminal height"`.
- `max(10, terminal_lines - 10)` on a tiny terminal (5 lines) returns 10 and may still overflow. Low priority since 5-line terminals are pathological.

### B3 — cli.py (bubble row numbers)

**Overall: Correct logic and well tested.**

- Two-pass pre-computation is readable and correct. `show_row_numbers = bool(truncated_rows)` is concise.
- Both conditional tests (`test_bubble_does_not_number_rows_without_truncation`, `test_bubble_numbers_rows_when_labels_are_truncated`) exist and cover the main cases.
- `max_label_width = 44` is hardcoded at line 785 with no way to customise — acceptable for now but note if a future `--max-label-width` option is added.

### B6 — renderer.py (duplicate txt labels)

**Overall: Correct, tests are sufficient for the primary scenario.**

- `txt_by_sub_row` changed from `str` to `list[str]` with dedup logic (`if seg.txt_label not in values`). Join with `", "` is reasonable.
- Test validates the primary multi-layer case.
- **Minor:** No test for duplicate txt values within a single sub_row (e.g. two segments on the same row with the same txt). The dedup logic handles it silently — a comment explaining that intention would help.

### B7 — renderer.py (`_LAYER_OFFSET` reduction)

**Overall: Visually correct, no regression guard.**

- Reducing `_LAYER_OFFSET` from `0.45` to `0.20` is a pure visual tuning change and not directly testable with plotext output.
- **Risk:** No test validates that a 3-row, 2-layer timeline produces exactly 3 y-tick labels (as the plan required). The plan's own test criterion was: *"assert exactly 3 y-tick labels (not 6)"*. This test was not written. Add it to the renderer test file using `--format compact` output.

### B9 — renderer.py (legend marker hints)

**Overall: Good UX improvement, one undocumented decision.**

- `[marker=hd]` / `[marker=sd]` notation in legend entries is clear. `_marker_for_layer()` reduces duplication well.
- **Unexplained change:** Marker order changed from `["hd", "braille", "dot", "sd"]` to `["hd", "sd", "braille", "dot"]`. The commit message doesn't explain why `braille` and `sd` were swapped. Add a comment in `renderer.py` near the `_LAYER_MARKERS` constant explaining the chosen order (e.g. coarse → fine grain, or most→least visually distinct).
- Tests check for `marker=hd` and `marker=sd` in legend text — sufficient coverage.

---

## Priority 1: Follow-up Tasks

- [x] **B8-test**: Added `test_malformed_bar_data_raises_clear_error` and `test_malformed_line_data_raises_clear_error` in `tests/test_reader.py` (completed 2026-02-18)
- [x] **B7-test**: Added `test_two_layer_timeline_has_correct_y_tick_count` in `tests/test_renderer.py` (completed 2026-02-18)
- [x] **B4-doc**: Added inline comment in `cli.py` near auto_max_rows explaining `--sample` + auto-truncate precedence (completed 2026-02-18)
- [x] **B9-doc**: Added comment to `_LAYER_MARKERS` constant explaining marker ordering rationale (completed 2026-02-18)

---

## Priority 2: UX Improvements (Issues #1 + #2)

### U1. Bar chart: integer y-axis ticks

**Problem:** Y-axis shows `577.0` instead of `577` for count-based bars.
**Fix:** When all values are integers, force integer tick formatting.
**Files:** `src/csvplot/renderer.py`

### U2. Bar chart: label bars with counts

**Problem:** No way to see exact values on bars.
**Fix:** Add `--labels` flag to print count above/inside each bar.
**Files:** `src/csvplot/renderer.py`, `src/csvplot/cli.py`

### U3. Line chart: missing legend for multiple series

**Problem:** Multiple `--y` columns plotted but no legend shows which color is which.
**Fix:** Always render legend when >1 series.
**Files:** `src/csvplot/renderer.py`

### ~~U4.~~ Summarise: `--sample` rows label — Already implemented

`cli.py:623` already creates the sample table with `title=f"Sample ({len(sample_rows)} random rows)"`. No action needed.

### ~~U5.~~ Completed (2026-02-18) — Error messages: list valid column names

**Problem:** Non-existent column → generic error. Should list available columns.
**Fix:** Catch `KeyError` for columns, print `"Column 'foo' not found. Available: bar, baz, ..."`.
**Files:** `src/csvplot/reader.py`, `src/csvplot/bubble.py`
**Status:** Implemented consistent missing-column validation in loaders and CLI key-error formatting; errors now include `"Available: ..."` across commands.

### ~~U6.~~ Completed (2026-02-18) — `--where` for empty/null values is awkward

**Problem:** `--where "COL=''"` feels unnatural. No autocomplete for empty values.
**Fix:** Support `--where "COL="` (trailing `=` with no value) as shorthand for empty/null match. Add `(empty)` to autocomplete suggestions.
**Files:** `src/csvplot/reader.py`, `src/csvplot/completions.py`
**Status:** Implemented empty/null shorthand matching in filters (`COL=` matches empty, null/none/na/nan) and added `COL=(empty)` suggestions in `--where` autocomplete.

---

## Priority 3: Feature Requests (deferred/larger scope)

These are valid but require more design work. Track separately.

| # | Feature | Source |
|---|---------|--------|
| F1 | `--group-by` for timeline aggregation | Issue #1 |
| F2 | Numeric conditionals (`--y-int`, `--where "age>30"`) | Issue #1 |
| F3 | PNG/SVG export (`--export chart.png`) | Issue #1 comment |
| F4 | File-first CLI syntax (`csvplot --file <f> bubble`) | Issue #1 comment |
| ~~F5~~ | ~~`--sort` for bar charts~~ — **Already implemented** (`cli.py:314-319`: `--sort {value\|label\|none}`) | ~~Issue #2~~ |
| F6 | `--ymin` / `--ymax` for line charts | Issue #2 |
| F7 | `--symbol` for bubble marker character | Issue #2 |
| F8 | `--palette` for color theming | Issue #2 |
| F9 | `.csvplot.toml` config file | Issue #2 |
| F10 | `--legend <position>` control | Issue #2 |
| F11 | Row sorting for timeline (by start date, etc.) | Issue #2 |
| F12 | Composite `--y` labels for bubble (multiple `--y` joined with ` \| `) | Issue #1 |

---

## Implementation Order

```
Phase 1 — Bug fixes (B2–B9, 7 items — B1 reclassified to F12)
  Completed on 2026-02-18 (commits: `be2f253`, `d5e723e`, `c9f0349`, `9d59cf8`, `5918682`)

Phase 2 — UX polish (U1–U3 — U4/U5/U6 already done)
  Target: improved error messages, legends, labels, and filtering UX
  Scope: ~5 changes, mostly in renderer and cli

Phase 3 — Features (F1–F4, F6–F12 — F5 already done)
  Target: pick top 3 by user demand, design + implement
  Requires separate design docs per feature
```

---

## Verification Checklist

For every change:
1. Write failing test first (TDD per CLAUDE.md)
2. Run `uv run pytest` — all green
3. Run `uv run ruff check src/ tests/` — no lint errors
4. Manual CLI check with `--format compact` (per CLAUDE.md)
5. Nano commit with conventional message
