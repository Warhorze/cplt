# csvplot

A CLI tool for plotting timeline/Gantt-style ranges from CSV files directly in the terminal.

## Why csvplot?

There are plenty of terminal charting tools (YouPlot, plotext, gnuplot), but none of them handle **timeline/Gantt-style range plots** from CSV out of the box. If you've ever needed to debug overlapping validity windows, visualize project timelines, or inspect SLA ranges -- and you wanted to do it without leaving the terminal -- there's nothing that just works.

csvplot fills that gap:

- Reads CSV, plots ranges in the terminal. That's it.
- Tab-completion for column names so you don't have to memorize your schema
- Date columns auto-detected -- only datetime columns offered for `--x`
- Open-ended ranges (NULL, `9999-12-31`) handled by default
- No browser, no GUI, no notebooks required

---

## Quick Start

```bash
pip install -e .
csvplot --install-completion  # enable tab-completion (restart shell after)
```

Simple example:

```bash
csvplot timeline -f data.csv \
  --x start_date --x end_date \
  --y category
```

Advanced example with two layers, coloring, and a marker:

```bash
csvplot timeline -f data/timeplot.csv \
  --x DH_PV_STARTDATUM --x DH_PV_EINDDATUM \
  --x EN_START_DATETIME --x EA_END_DATETIME \
  --y DH_FACING_NUMMER \
  --color SH_ARTIKEL_S1 \
  --marker 2025-01-22 --marker-label "wissel-datum"
```

---

## CLI Reference

### `csvplot timeline`

Plot timeline/Gantt-style ranges from a CSV file.

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--file`, `-f` | Yes | | Path to CSV file |
| `--x <col>` | Yes (2+) | | Time-range columns as start/end pairs |
| `--y <col>` | Yes (1+) | | Categorical Y-axis column(s); repeat to combine |
| `--color <col>` | No | | Color segments by this column |
| `--txt <col>` | No | | Label segments with this column's value |
| `--marker <date>` | No | | Vertical marker line (YYYY-MM-DD) |
| `--marker-label <text>` | No | | Label for the marker |
| `--head <n>` | No | | Only read the first N CSV rows |
| `--open-end / --no-open-end` | No | `--open-end` | Replace NULL/sentinel end dates with today |

The `--x` option takes start/end column pairs. Provide 2 values for a single layer, 4 for two layers, etc:

```bash
# 1 layer
csvplot timeline -f data.csv --x START --x END --y category

# 2 layers
csvplot timeline -f data.csv --x S1 --x E1 --x S2 --x E2 --y category
```

You can repeat `--y` to build a composite y-label:

```bash
csvplot timeline -f data.csv --x START --x END --y category --y name
```

### Tab completion

After running `csvplot --install-completion`, column-name options complete from the CSV headers:

- `--x` suggests **datetime columns** with smart ordering (start-like columns first at even positions, end-like columns first at odd positions)
- `--y`, `--color` suggest **all columns**
- `--file` uses standard filesystem completion

Requires `--file` to appear before the column options on the command line.

### Open-end handling

By default, NULL or sentinel end dates (`9999-12-31`) are replaced with today's date so ranges are always visible. Pass `--no-open-end` to skip rows with missing end dates instead.

---

## Dependencies

- **Typer** -- CLI framework with shell completion
- **Rich** -- Terminal formatting
- **Plotext** -- Terminal plotting backend
- **csv** (stdlib) -- CSV parsing

No pandas. The stdlib `csv` module is all that's needed for the current scope.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

### Project structure

```
src/csvplot/
  cli.py          # Typer app, argument definitions
  reader.py       # CSV reading, datetime parsing, segment loading
  models.py       # Segment, Marker, PlotSpec dataclasses
  renderer.py     # PlotSpec -> plotext -> terminal
  completions.py  # Column-name tab completion with date detection
```
