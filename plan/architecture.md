# csvplot Architecture Snapshot

Last updated: 2026-02-15

This document reflects the **current** implementation state (not initial scaffolding plans).

## Current Scope

csvplot is a terminal-first CLI for CSV exploration and visualization with five commands:

- `timeline` — Gantt/range plotting from start/end date pairs
- `bar` — value-count charts from categorical columns
- `line` — numeric series over x-axis columns
- `bubble` — presence/absence matrix for selected columns
- `summarise` — per-column profiling and optional random row samples

All commands support filtering with `--where` / `--where-not` and output modes `visual`, `semantic`, and `compact`.

## Module Layout

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

## Data Flow

```text
CLI args
  -> parse/validate options
  -> load data from CSV (reader/bubble/summarise)
  -> build spec or summary objects
  -> render in selected format (visual | semantic | compact)
  -> terminal output
```

## Key Behavior Contracts

- Timeline `--x` values are required in start/end pairs (even count, at least 2).
- Multi-`--y` values are combined into one flat label via `" | "`.
- Bubble uses `--cols` as the primary matrix-column option.
- Filtering is case-insensitive by default for both column names and values.
- Completion for `--where` resolves columns case-insensitively and preserves canonical CSV casing in suggestions.
- `--format` is validated consistently across commands: `visual`, `semantic`, `compact`.

## Known UX Debt (tracked in `plan/improvements.md`)

- Bubble `--color` is accepted but currently does not produce distinct row-color behavior.
- Some format-specific options are intentionally ignored in compact mode (`timeline --txt`, `bar --horizontal`).
