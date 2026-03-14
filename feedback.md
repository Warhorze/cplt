# cplt Tester Feedback

Date: 2026-02-14
Tester: Claude Code (second pass, validating + extending Codex's original review)

## Bottom line

All 175 tests pass. All 5 commands (timeline, bar, line, bubble, summarise) work correctly with the bundled `data/` files. Several issues from the original review have been fixed. A few remain, plus new findings.

## Status of previously reported findings

### Fixed since original review

1. **`--where` column names are now case-insensitive** (was finding #4)
   - `--where "sex=male"`, `--where "SEX=female"`, `--where "Sex=MALE"` all work identically.
   - Help text matches behavior: both column names and values are case-insensitive.

2. **`line` no longer crashes on blank/invalid x dates** (was finding #3)
   - Tested with synthetic CSV containing empty and "invalid" date strings in x column.
   - Invalid rows are silently skipped; 3 valid points rendered from 5-row CSV.

3. **`bubble --cols` docs now use correct repeated-flag syntax** (was finding #1)
   - README line 44: `--cols Cabin --cols Age --cols Embarked` (correct).
   - Space-separated `--cols Cabin Age Embarked` still fails as expected (Typer limitation).

### Still present

4. **`timeline --open-end` silently drops rows with invalid (non-empty, non-sentinel) end dates** (was finding #2, behavior changed)
   - Original report: invalid end dates were converted to "open now".
   - Current behavior: rows with unparseable non-empty end dates (e.g. "baddate") are silently dropped entirely — not shown, no warning.
   - Empty end dates and sentinel dates (9999-12-31) correctly get open-end treatment.
   - This is arguably better than the old behavior (no silent misrepresentation), but still a data loss risk since the user gets no indication that rows were skipped.

5. **`summarise` top-value notation is still unclear** (finding #6)
   - `1(1), 2(1), 3(1)` format has no legend explaining that `(N)` means frequency.
   - The column header says "Top Values" but doesn't clarify the format.

6. **Bar charts still use ANSI colors by default without `--color` flag** (finding #5)
   - Bar command has no explicit color-control option.
   - Low priority — this is standard plotext behavior and only affects visual mode.

## New findings

### 7. Compact line min/max shows excessive decimal places (Low UX)
- Repro: `cplt line -f data/temperatures.csv --x Date --y Temp --format compact`
- Output: `(min=6.30655737704918 max=17.698333333333334)`
- These are averaged values from downsampling, but the precision is excessive.
- Suggest rounding to 2 decimal places for readability.

### 8. `--txt` labels are not rendered in compact format (Low, by design?)
- Repro: `cplt timeline -f data/projects.csv --x start_date --x end_date --y project --txt status --format compact`
- The `--txt` option is accepted without error but produces identical output to without it.
- Compact format uses RLE-encoded bars where there's no room for text labels, so this may be intentional — but the option should either be documented as visual-only or produce some compact representation.

### 9. `--horizontal` has no effect in compact bar format (Low, by design?)
- Repro: `cplt bar -f data/titanic.csv -c Pclass --horizontal --format compact`
- Output is identical to non-horizontal compact output.
- Makes sense since compact bars are always horizontal RLE-encoded, but the flag is silently ignored.

### 10. README project structure is incomplete (Low, docs)
- `data/projects.csv` not listed in the data files section (line 216).
- `src/cplt/compact.py`, `bubble.py`, `summarise.py` not listed in project structure (lines 207-213).
- `--format` option not mentioned anywhere in README (users may not discover compact mode).
- `--where`/`--where-not` not listed in individual command tables (only in separate "Filtering" section) — inconsistent with how `--head` is listed per-command.
- `summarise` command missing from Quick Start examples.

## Validation results

### All commands tested with compact output

```
# timeline — 15 segments, 3 status groups, correct color legend
cplt timeline -f data/projects.csv --x start_date --x end_date --y project --color status --format compact

# bar — counts match: 3=491, 1=216, 2=184
cplt bar -f data/titanic.csv -c Pclass --format compact

# line — 3650 points, date range 1981-01-01..1990-12-31
cplt line -f data/temperatures.csv --x Date --y Temp --format compact

# bubble — presence/absence matches CSV null/non-null row-by-row
cplt bubble -f data/titanic.csv --cols Cabin --cols Age --cols Embarked --y Name --head 8

# summarise — correct row counts, type detection, top values
cplt summarise -f data/projects.csv
```

### Filtering validated

| Test | Command | Result |
|------|---------|--------|
| `--where` single | `bar ... --where "Sex=male"` | 577 male rows |
| `--where` case-insensitive col | `bar ... --where "sex=male"` | Same 577 rows |
| `--where` case-insensitive val | `bar ... --where "Sex=MALE"` | Same 577 rows |
| `--where` multiple (AND) | `bar ... --where "Sex=male" --where "Embarked=S"` | 265+97+79=441 (correct subset) |
| `--where-not` | `timeline ... --where-not "status=Planning"` | 12 rows (15 - 3 Planning) |
| `--where` + `--where-not` | `timeline ... --where "team=Backend" --where-not "status=Done"` | 2 rows (correct) |
| `--where` no match | `bar ... --where "Pclass=999"` | "Warning: No data found in the column." |
| `--where` bad format | `bar ... --where "badformat"` | "Error: Expected format COL=value" |

### Options validated

| Feature | Command | Result |
|---------|---------|--------|
| `--sort value` | `bar -c Embarked --sort value` | S(644), C(168), Q(77), empty(2) |
| `--sort label` | `bar -c Embarked --sort label` | empty(2), C(168), Q(77), S(644) |
| `--sort none` | `bar -c Embarked --sort none` | S, C, Q, empty (CSV first-appearance order) |
| `--top N` | `bar -c Pclass --top 2` | Only 3(491), 1(216) shown |
| `--head N` | `line --head 100` | 100 points, range 1981-01-01..1981-04-10 |
| `--from/--to` | `timeline --from 2026-01-01 --to 2026-04-01` | Correctly zoomed date range |
| `--marker` | `timeline --marker 2026-01-01 --marker-label "New Year"` | Marker in compact output |
| Multi-layer | `timeline --x S1 --x E1 --x S2 --x E2` | `█` for layer 0, `#` for layer 1 |
| Multi-`--y` | `timeline --y team --y project` | Composite labels "Backend \| Auth service" |
| `--y-detail` | `timeline --y team --y-detail project` | Same composite grouping |
| `--color` (bubble) | `bubble --color Pclass` | Accepted, renders with Rich colors |
| `--sample N` | `summarise --sample 3` | Shows 3 random sample rows below summary |
| `--open-end` | `timeline` with empty end date | Extended to today (2026-02-14) |
| `--no-open-end` | `timeline --no-open-end` | Row with empty end dropped, 6 of 7 shown |

### Error handling validated

| Scenario | Result |
|----------|--------|
| Nonexistent file | "File 'data/nonexistent.csv' does not exist." (exit 2) |
| Nonexistent column | "Column not found in CSV: 'NonExistentCol'" (exit 1) |
| No matching data | "Warning: No data found." / "Warning: No data found in the column." |
| Bad `--where` format | "Error: Expected format COL=value, got 'badformat'" (exit 1) |
| Blank/invalid dates in line x | Silently skipped, valid points rendered |

## Test suite

- **175 tests, all passing** (pytest 9.0.2, Python 3.12.9)
- Test files: test_bubble, test_compact, test_completions, test_completions_where, test_filter, test_models, test_reader, test_summarise
- Runtime: ~1.4s

## Recommendations (prioritized)

1. **Warn when rows are silently dropped** (finding #4) — When `--open-end` is on and a row has a non-empty but unparseable end date, emit a stderr warning like "Warning: skipped 1 row(s) with unparseable end dates". This prevents silent data loss.

2. **Round compact line min/max** (finding #7) — Format to 2 decimal places in `compact_line()`.

3. **Add `summarise` top-value legend** (finding #5) — Either add a table footnote ("Top Values format: value(frequency)") or rename the column header to "Top Values (freq)".

4. **Complete README project structure** (finding #10) — Add missing files (`compact.py`, `bubble.py`, `summarise.py`, `projects.csv`), document `--format compact`, and add a `summarise` Quick Start example.

5. **Document visual-only options** (findings #8, #9) — Note in help text that `--txt` and `--horizontal` have no effect in compact format, or implement compact representations.

## Command Log

```bash
# All commands used during this review (all with --format compact where supported)

# timeline
cplt timeline -f data/projects.csv --x start_date --x end_date --y project --color status --format compact
cplt timeline -f data/projects.csv --x start_date --x end_date --y project --color status --where "status=Done" --format compact
cplt timeline -f data/projects.csv --x start_date --x end_date --y project --where-not "status=Planning" --format compact
cplt timeline -f data/projects.csv --x start_date --x end_date --y project --color status --marker 2026-01-01 --marker-label "New Year" --format compact
cplt timeline -f data/projects.csv --x start_date --x end_date --y team --y project --color status --format compact
cplt timeline -f data/projects.csv --x start_date --x end_date --y team --y-detail project --color status --format compact
cplt timeline -f data/projects.csv --x start_date --x end_date --y project --txt status --format compact
cplt timeline -f data/projects.csv --x start_date --x end_date --y project --from 2026-01-01 --to 2026-04-01 --format compact
cplt timeline -f data/projects.csv --x start_date --x end_date --y project --where "team=Backend" --where "status=Done" --format compact
cplt timeline -f data/projects.csv --x start_date --x end_date --y project --where "team=Backend" --where-not "status=Done" --format compact
cplt timeline -f data/timeplot.csv --x EN_START_DATETIME --x EA_END_DATETIME --y DN_BRONSLEUTEL --format compact
cplt timeline -f data/timeplot.csv --x EN_START_DATETIME --x EA_END_DATETIME --y DN_BRONSLEUTEL --no-open-end --format compact
cplt timeline -f data/timeplot.csv --x DH_PV_STARTDATUM --x DH_PV_EINDDATUM --x EN_START_DATETIME --x EA_END_DATETIME --y DH_FACING_NUMMER --color SH_ARTIKEL_S1 --marker 2025-01-22 --marker-label "wissel-datum" --format compact

# bar
cplt bar -f data/titanic.csv -c Pclass --format compact
cplt bar -f data/titanic.csv -c Sex --where "Sex=MALE" --format compact
cplt bar -f data/titanic.csv -c Sex --where "sex=male" --format compact
cplt bar -f data/titanic.csv -c Sex --where "SEX=female" --format compact
cplt bar -f data/titanic.csv -c Embarked --sort none --format compact
cplt bar -f data/titanic.csv -c Embarked --sort value --format compact
cplt bar -f data/titanic.csv -c Embarked --sort label --format compact
cplt bar -f data/titanic.csv -c Pclass --top 2 --format compact
cplt bar -f data/titanic.csv -c Pclass --horizontal --format compact
cplt bar -f data/titanic.csv -c Pclass --sort label --format compact
cplt bar -f data/titanic.csv -c Pclass --where "Sex=male" --where "Embarked=S" --format compact
cplt bar -f data/titanic.csv -c Pclass --where "Pclass=999" --format compact

# line
cplt line -f data/temperatures.csv --x Date --y Temp --format compact
cplt line -f data/temperatures.csv --x Date --y Temp --head 100 --format compact
cplt line -f data/temperatures.csv --x Date --y Temp --where "Temp=ZZZ" --format compact
cplt line -f /tmp/test_blank_dates.csv --x Date --y Temp --format compact

# bubble
cplt bubble -f data/titanic.csv --cols Cabin --cols Age --cols Embarked --y Name --head 8
cplt bubble -f data/titanic.csv --cols Cabin Age Embarked --y Name --head 3  # expected failure
cplt bubble -f data/titanic.csv --cols Cabin --cols Age --cols Embarked --y Name --top 2 --head 8
cplt bubble -f data/titanic.csv --cols Cabin --cols Age --cols Embarked --y Name --color Pclass --head 10

# summarise
cplt summarise -f data/projects.csv
cplt summarise -f data/titanic.csv --head 10
cplt summarise -f data/temperatures.csv
cplt summarise -f data/titanic.csv --where "Sex=male"
cplt summarise -f data/projects.csv --sample 3

# edge case: open-end with bad data
cplt timeline -f /tmp/test_bad_end.csv --x start --x end --y name --format compact
cplt timeline -f /tmp/test_bad_end.csv --x start --x end --y name --open-end --format compact
cplt timeline -f /tmp/test_empty_end.csv --x start --x end --y name --format compact
cplt timeline -f /tmp/test_sentinel_end.csv --x start --x end --y name --format compact

# error handling
cplt bar -f data/nonexistent.csv -c Pclass --format compact
cplt bar -f data/titanic.csv -c NonExistentCol --format compact
cplt bar -f data/titanic.csv -c Pclass --where "badformat" --format compact
cplt line -f data/temperatures.csv --x Date --y Temp --where "Temp=ZZZ" --format compact
```

## Verdict

cplt is solid and well-tested. The core data pipeline (CSV → loader → spec → render) is correct across all 5 commands and all bundled datasets. Filtering, sorting, multi-layer timelines, open-end handling, and error cases all behave as expected. The main remaining gaps are UX polish items (compact decimal formatting, summarise legend, docs completeness) and a missing warning for silently dropped rows with bad end dates.
