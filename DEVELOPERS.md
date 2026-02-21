# Developer Guide

This file is the single contributor reference for csvplot. User-facing docs live in `README.md`.

## Architecture

Data flows linearly: **CLI args → reader → PlotSpec → renderer → terminal**

```text
src/csvplot/
  cli.py          # Typer command definitions + arg validation
  reader.py       # timeline/bar/line CSV loaders + datetime parsing + row filters
  bubble.py       # bubble matrix loader + falsy detection
  summarise.py    # CSV summary/profiling logic
  models.py       # Segment/Marker/PlotSpec/BarSpec/LineSpec dataclasses
  renderer.py     # plotext visual rendering (timeline/bar/line)
  compact.py      # compact token-efficient rendering
  semantic.py     # ANSI-stripped rendering helpers
  completions.py  # column/date/value shell completion
```

### Key behavior contracts

- Timeline `--x` values are required in start/end pairs (even count, at least 2).
- Multi-`--y` values are combined into one flat label via `" | "`.
- Bubble uses `--cols` as the primary matrix-column option.
- Filtering is case-insensitive for both column names and values.
- `--format` is validated consistently across commands: `visual`, `semantic`, `compact`.
- Some flags are visual-only no-ops in compact mode (`--txt`, `--horizontal`).

### Known UX debt

Tracked in `plan/improvements.md`:

- Unparseable end dates in timeline are silently dropped (no warning).
- Bubble `--color` is accepted but behavior varies by format.

## Development Checks

```bash
uv sync --extra dev          # install with dev deps
bash scripts/run_cli_smoke.sh  # one-shot CLI smoke checks
uv run pytest                # run all tests
uv run pytest tests/ux/      # run UX tests only
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run pyright
```

## CLI Path Map

Every invocation follows: `csvplot <command> -f <file> <required args> [optional args]`
`--format <fmt>` is optional on every command (default: `visual`).

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
│   ├── [--vline DATE]                             ← vertical reference line
│   │   └── [--label TEXT]                        ← label for vline (has effect only with --vline)
│   ├── [--dot COL]                                ← per-row date markers (repeatable)
│   ├── [--open-end / --no-open-end]              ← null end → today (default: on)
│   └── [--from DATE] [--to DATE]                 ← zoom into date range
│
├── bar -f FILE
│   ├── --column COL / -c COL                     ← required
│   ├── [--sort {value|label|none}]               ← sort order (default: value)
│   ├── [--horizontal]                            ← horizontal bars (visual only)
│   ├── [--labels]                                ← show bar value labels (visual only)
│   └── [--top N]                                 ← show only top N categories
│
├── line -f FILE
│   ├── --x COL                                   ← required (single x-axis column)
│   ├── --y COL                                   ← required (at least 1)
│   │   └── [--y COL ...]                         ← multiple series on same chart
│   └── [--color COL]                             ← split into grouped lines
│
├── bubble -f FILE
│   ├── --cols COL                                ← required (at least 1)
│   │   └── [--cols COL ...]                      ← additional matrix columns
│   ├── --y COL                                   ← required (row label column)
│   ├── [--color COL]                             ← color rows by column
│   ├── [--top N]                                 ← top N columns by fill-rate
│   ├── [--sort {fill|fill-asc|name}]             ← sort rows by fill-rate or name
│   ├── [--transpose / --no-transpose]            ← swap rows and columns
│   ├── [--group-by COL]                          ← aggregate fill-rates per group
│   └── [--encode / --no-encode]                  ← auto-encode: ≤2 unique → binary, >2 → one-hot
│
└── summarise -f FILE
    └── [--sample N]                              ← show N random rows below summary
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

### Option interactions

```
--label ────────requires──▶ --vline
--dot ──────────only affects──▶ timeline
--txt ──────────only affects──▶ --format visual
--horizontal ───only affects──▶ --format visual
--labels ───────only affects──▶ --format visual
--open-end ─────only affects──▶ timeline
--sample ───────only affects──▶ summarise
--y-detail ─────only affects──▶ timeline
--top ──────────only on──▶ bar, bubble (different semantics)
--color ────────on──▶ timeline (segment color), line (group-by), bubble (row color)
--x ────────────on──▶ timeline (date pairs, even count), line (single column)
--y ────────────on──▶ timeline (list, composite), line (list, multi-series), bubble (single, label)
--sort ─────────only on──▶ bar (value/label/none), bubble (fill/fill-asc/name)
--transpose ───only on──▶ bubble
--group-by ────only on──▶ bubble (aggregates per group, separate code path)
--encode ──────only on──▶ bubble (≤2 unique non-falsy and >2 unique both use col=value columns)
```

## UX Review

### Manual visual review

Use this loop when reviewing chart quality and regressions:

1. Generate showcase images and design review artifacts:

```bash
bash scripts/generate_readme_images.sh
bash scripts/generate_design_review_images.sh
```

2. Review the generated report and plot-specific criteria:

- `assets/review/REPORT.md` — generated review summary
- `assets/review/images/` — PNG captures
- `assets/review/raw/` — raw command outputs

3. For color behavior (e.g. bubble `--color`), compare PNGs with and without the flag.

### Review artifacts: what lives where

- `assets/review/SCENARIOS.md` defines what to run: canonical scenario list, exact `csvplot` commands, and intent for each scenario.
- `assets/review/REPORT.md` is run output: generated artifact links/previews plus automated check outcomes from the latest run.

### Cross-cutting UX checklist

Apply these checks across all plot types during review:

- `--color` has a non-color fallback cue (symbol/style) for low-color terminals and screenshots.
- Missing categorical values surface explicitly (e.g. `(missing)`) instead of unlabeled buckets.
- Date tick formatting adapts to visible time span to reduce axis noise.
- Row labels use truncation + reference table when they dominate matrix readability.
- Compact interpretation summaries (e.g. top category, missing count) improve scanability.

### Automated UX tests

The `tests/ux/` suite covers functional CLI behavior end-to-end:

- **Format matrix** — 5 commands x 3 formats = 15 parameterized cases (`test_format_matrix.py`)
- **Option behavior** — per-command checks for every optional flag (`test_options_ux.py`)
- **Combination matrix** — pairwise/triple cross-stage interactions per command:
  - `test_bubble_combinations.py`
  - `test_bar_combinations.py`
  - `test_timeline_combinations.py`
  - `test_line_combinations.py`
  - `test_summarise_combinations.py`
- **Error message quality** — guards that errors are actionable, not tracebacks (`test_error_ux.py`)
- **Scale** — 500–10K row stress tests (`test_scale_ux.py`)

See `plan/ux-testing.md` for the full coverage matrix and test design.
See `plan/combination-matrix.md` for the cross-stage pipeline model and rollout order.

### UX tester flow (combination-first)

Run UX checks in this order to catch option-interaction regressions early:

1. Bubble combinations (`tests/ux/test_bubble_combinations.py`)
2. Encode scale guardrails (`tests/ux/test_scale_ux.py`)
3. Timeline combinations (`tests/ux/test_timeline_combinations.py`)
4. Bar combinations (`tests/ux/test_bar_combinations.py`)
5. Line combinations (`tests/ux/test_line_combinations.py`)
6. Summarise combinations (`tests/ux/test_summarise_combinations.py`)
7. Full UX suite (`tests/ux/`)
8. Lint + type + full tests

Recommended command sequence:

```bash
uv run pytest tests/ux/test_bubble_combinations.py -v
uv run pytest tests/ux/test_scale_ux.py -v
uv run pytest tests/ux/test_timeline_combinations.py -v
uv run pytest tests/ux/test_bar_combinations.py -v
uv run pytest tests/ux/test_line_combinations.py -v
uv run pytest tests/ux/test_summarise_combinations.py -v
uv run pytest tests/ux/ -v -rXx
uv run ruff check src/ tests/
uv run pyright
uv run pytest
```

Notes:

- `-rXx` surfaces unexpected pass/fail drift for expected-fail tests so stale `xfail` markers are removed quickly.
- Treat option order as invariant in combo tests: `A+B` and `B+A` must produce equivalent behavior.
- No-op combinations must either work end-to-end or emit an explicit, actionable error.

## Design Review Criteria

Each plot type has acceptance criteria for visual review. Full docs with feedback history live in `docs/design/`.

### Timeline

- Clear x-axis date progression; readable composite y-labels
- Multi-layer segments are visually distinguishable (different glyphs per layer)
- Legend maps encodings to source columns/values when `--color` is used
- Vline and label are visible and positioned correctly
- Rows skipped due to invalid dates should surface a warning

### Bar

- Category labels readable and aligned; count scale shows relative magnitude
- Sort mode (`value`, `label`, `none`) is reflected correctly in output
- `--top N` shows only the expected categories
- `--horizontal` is visual-only (no effect in compact)

### Line

- Continuous line trajectories for valid points; chronological x-axis ordering
- Invalid/blank x values handled without crash (silently skipped)
- Compact min/max labels are human-readable (no excessive decimal precision)
- Multiple `--y` series remain distinguishable

### Bubble

- Clear present/absent markers in matrix grid
- Row labels and column headers remain legible at default terminal width
- `--top N` returns the most-filled columns
- `--color` visibly changes visual output (Legend section appears)
- `--sort` reorders rows correctly (fill/fill-asc by fill-rate, name alphabetical)
- `--transpose` swaps rows ↔ columns; fill-rate footer adapts
- `--group-by` shows one row per group with fill-rate percentages and TOTAL footer
- `--encode` uses `col=value` columns for both binary (≤2 unique non-falsy) and categorical (>2 unique) data; empty values get `col=(empty)` when included

### Summarise

- Correct row counts and type detection
- Top-value notation is self-explanatory (frequency format clear)
- `--sample N` produces a labelled sample section

## Docs Tooling

Regenerate CLI docs:

```bash
bash scripts/generate_cli_docs.sh
```

Regenerate README images:

```bash
bash scripts/generate_readme_images.sh
```

Generate design review artifacts:

```bash
bash scripts/generate_design_review_images.sh
```

Preview MkDocs site locally:

```bash
uv sync --extra docs
uv run mkdocs serve
```

## Ready for Release

Run through this checklist before tagging a release:

1. **Tests pass**

   ```bash
   uv run pytest
   ```

2. **Lint and format clean**

   ```bash
   uv run ruff check src/ tests/
   uv run ruff format --check src/ tests/
   uv run pyright
   ```

3. **CLI smoke test**

   ```bash
   bash scripts/run_cli_smoke.sh
   ```

4. **Visual inspection** — generate design review artifacts and review PNGs for regressions:

   ```bash
   bash scripts/generate_design_review_images.sh
   ```

   Review `assets/review/REPORT.md` and spot-check PNGs in `assets/review/images/`.

5. **Demo GIFs up-to-date** — re-record if any CLI output or command syntax changed:

   ```bash
   bash scripts/generate_demos.sh
   ```

   Verify GIFs in `assets/images/` reflect current behavior.

6. **CLI docs current**

   ```bash
   bash scripts/generate_cli_docs.sh
   ```

   Check `docs/cli.md` matches the current command surface.

7. **Bump version, changelog, and tag**

   ```bash
   cz bump --dry-run        # preview version bump and changelog
   cz bump                  # bump pyproject.toml version, update CHANGELOG.md, commit, and tag
   ```

8. **Push release**

   ```bash
   git push origin main --tags
   ```
