# csvplot Implementation Plan

## Context

csvplot is a greenfield Python CLI tool for plotting timeline/Gantt-style ranges from CSV files in the terminal. No code exists yet — just `readme.md` and a sample CSV (`data/timeplot.csv`, 7 rows, 24 columns). No existing tools in the ecosystem handle terminal Gantt plots from CSV.

## File Tree

```
csvplot/
  pyproject.toml
  readme.md
  data/
    timeplot.csv
  src/
    csvplot/
      __init__.py
      __main__.py        # python -m csvplot
      cli.py             # Typer app, args, completion hooks
      reader.py          # CSV reading + datetime parsing
      models.py          # Dataclasses: Segment, Marker, PlotSpec
      renderer.py        # plotext rendering
      completions.py     # Column-name completion (header cache)
  tests/
    __init__.py
    conftest.py
    test_reader.py
    test_models.py
```

## Module Design

### `models.py` — Core data structures (zero deps)

```python
@dataclass(frozen=True, slots=True)
class Segment:
    layer: Layer          # PRIMARY | SECONDARY
    y_label: str          # categorical Y value
    start: datetime
    end: datetime
    color_key: str = ""

@dataclass
class Marker:
    date: datetime
    label: str = ""

@dataclass
class PlotSpec:
    segments: list[Segment]
    markers: list[Marker]
    view_start: datetime | None = None
    view_end: datetime | None = None
```

### `reader.py` — CSV → Segments

- `read_csv_header(path)` — reads first line only (stdlib `csv.reader`)
- `parse_datetime(value)` — tries 3 formats, returns `None` for empty/`9999-*` sentinels
- `load_segments(path, x_start, x_end, y_col, ...)` — iterates `csv.DictReader`, emits `Segment` per row per layer

### `renderer.py` — PlotSpec → terminal

Uses `plt.plot([start, end], [y, y])` per segment (not `plt.bar()`). This avoids bar-width conflicts and naturally supports overlapping layers at the same y-position. Primary segments use full-block markers, secondary use lighter markers. Color mapping via deterministic palette cycling.

### `cli.py` — Typer app

Single `plot` command. `--x` takes a `list[str]` validated to length 2 in the function body (Typer lacks nargs=2). All column-name options get `autocompletion=complete_column`.

### `completions.py` — Tab completion

Reads `--file` from `ctx.params`, calls `read_csv_header`, caches by `(resolved_path, mtime)`. Returns filtered column names matching the incomplete prefix. `--file` must precede column options on the command line (documented Click limitation).

## Data Flow

```
CLI args → reader.load_segments() → list[Segment]
                                          ↓
                              cli.py builds PlotSpec
                                          ↓
                              renderer.render(PlotSpec)
                                          ↓
                              plotext → terminal output
```

## Key Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| No pandas | stdlib `csv.DictReader` | Explicit requirement. 7 rows don't justify it. |
| Rendering | `plt.plot()` per segment | Simpler than bar tricks. Overlapping layers work naturally. |
| Dataclasses | `frozen=True, slots=True` | Immutable, lightweight, good IDE support. |
| Datetime parsing | `strptime` with 3 formats | Covers sample data. No dateutil dep needed. |
| `--x` args | `list[str]` + len check | Pragmatic Typer workaround. Fallback: `--x-start`/`--x-end`. |

## Implementation Order

### Step 1: Scaffold
- Create `pyproject.toml` (deps: typer, rich, plotext; scripts entry; ruff config)
- Create directory structure + `__init__.py`, `__main__.py`
- Stub `cli.py` with bare Typer app
- Verify `pip install -e .` and `csvplot plot --help`

### Step 2: Models + Reader
- Implement `models.py` (Segment, Marker, PlotSpec, Layer enum)
- Implement `reader.py` (header reading, datetime parsing, segment loading)
- Write `tests/test_reader.py` (parametrized: normal dates, empty, sentinel, bad format, segment extraction from sample CSV)

### Step 3: Renderer
- Implement `renderer.py` (segment plotting, color mapping, markers, date axis)
- Manual visual verification with sample data

### Step 4: CLI Wiring
- Wire cli.py: connect reader → PlotSpec → renderer
- Argument validation, friendly error messages via Rich
- End-to-end test: `csvplot plot --file data/timeplot.csv --x DH_PV_STARTDATUM DH_PV_EINDDATUM --y DH_FACING_NUMMER`

### Step 5: Completion
- Implement `completions.py`
- Hook into cli.py options
- Test with `csvplot --install-completion`

### Step 6: Polish
- `--color` with palette cycling
- `--open-end` replacement
- `--marker` / `--marker-label`
- Zoom window cropping

## Verification

1. `pip install -e .` succeeds
2. `csvplot plot --help` shows all options
3. `csvplot plot --file data/timeplot.csv --x DH_PV_STARTDATUM DH_PV_EINDDATUM --y DH_FACING_NUMMER` renders a visible timeline
4. Adding `--x2`, `--color`, `--marker`, `--open-end` each works incrementally
5. `pytest` passes all unit tests
6. Tab completion works after `--install-completion`

## Risks

- **plotext datetime axis**: If date strings don't render on horizontal plots, fallback is numeric timestamps with manual tick labels
- **Typer `list[str]` for `--x`**: May require `--x val1 --x val2` syntax instead of `--x val1 val2`. Test early in Step 1.
- **Completion context**: `--file` must come before column options. Documented limitation.
