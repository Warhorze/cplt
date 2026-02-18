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
uv run pytest                # run all tests
uv run pytest tests/ux/      # run UX tests only
uv run ruff check src/ tests/
uv run ruff format src/ tests/
uv run pyright
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
- **Error message quality** — guards that errors are actionable, not tracebacks (`test_error_ux.py`)
- **Scale** — 500–10K row stress tests (`test_scale_ux.py`)

See `plan/ux-testing.md` for the full coverage matrix and test design.

## Design Review Criteria

Each plot type has acceptance criteria for visual review. Full docs with feedback history live in `docs/design/`.

### Timeline

- Clear x-axis date progression; readable composite y-labels
- Multi-layer segments are visually distinguishable (different glyphs per layer)
- Legend maps encodings to source columns/values when `--color` is used
- Marker line and label are visible and positioned correctly
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
