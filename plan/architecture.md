# csvplot Implementation Plan

## Context

csvplot is a greenfield Python CLI tool for plotting timeline/Gantt-style ranges from CSV files in the terminal. No code exists yet — just `README.md` and a sample CSV (`data/timeplot.csv`, 7 rows, 24 columns). No existing tools in the ecosystem handle terminal Gantt plots from CSV.

## File Tree

```
csvplot/
  pyproject.toml
  README.md
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

New Findings:

Findings (prioritized)

  1. High: bubble --color is accepted but not applied in rendering

  - src/csvplot/cli.py:578 exposes --color (“Color rows by this column”).
  - src/csvplot/bubble.py:71 loads color_keys.
  - src/csvplot/cli.py:654 renders all truthy cells as hardcoded [green]●[/green], never using spec.color_keys.
  - Impact: user-visible feature contract is broken; option appears to work but is ignored.

  2. High: line --color drops data for duplicate (group, x) points (last-write-wins)

  - src/csvplot/reader.py:420 stores grouped values as dict[str, float] per group.
  - src/csvplot/reader.py:432 assigns groups[group_key][x_val] = float(...), overwriting prior points with same x.
  - Impact: silent data loss for common time-series shapes (multiple observations per period per group), with no warning or aggregation policy.

  3. Medium: timeline command swallows all loader exceptions, reducing diagnosability

  - src/csvplot/cli.py:210 catches broad Exception and prints generic “Failed to read CSV”.
  - Other commands only catch KeyError and let unexpected errors surface.
  - Impact: inconsistent error behavior and harder debugging of real parsing/logic failures.

  4. Medium: --where autocompletion is case-sensitive for column lookup, while runtime filtering is now case-insensitive

  - src/csvplot/completions.py:189 rejects col unless exact-case match.
  - Runtime filtering resolves columns case-insensitively (src/csvplot/reader.py:127).
  - Impact: UX inconsistency; completion fails for valid expressions like sex=... when CSV has Sex.

  5. Medium: summarise --sample does full-row buffering (O(n) memory)

  - src/csvplot/summarise.py:90 allocates all_rows when sampling is enabled.
  - src/csvplot/summarise.py:115 appends every row before random.sample.
  - Impact: avoidable memory growth on large files; reservoir sampling would keep memory O(sample_n).

  6. Medium: gap in CLI integration test coverage

  - Current tests focus on loaders/completions/unit behavior (tests/test_reader.py, tests/test_filter.py, etc.) but there is no command-level CLI
    test module (for example no tests/test_cli.py).
  - Impact: user-facing regressions (arg parsing/help/option wiring) are more likely to slip through.

  Open questions / assumptions

  1. For duplicate grouped line points, should behavior be mean, sum, min/max, or explicit error?
  2. For timeline loader failures, do you want strict failure (raise) or warn-and-skip-row semantics?

  Current architecture snapshot

  - Overall layering is clear and mostly clean: CLI orchestration (src/csvplot/cli.py) -> data loaders (src/csvplot/reader.py, src/csvplot/
    bubble.py, src/csvplot/summarise.py) -> rendering (src/csvplot/renderer.py) with typed specs (src/csvplot/models.py).
  - Main risks are now around feature-contract consistency and scale behavior, not fundamental structure.

---

## LLM Integration Flows

csvplot supports three output formats (`visual`, `compact`, `semantic`) designed for two distinct LLM-driven workflows.

### Flow 1: Scout & Presenter

A two-stage pipeline where an LLM explores a dataset and then presents findings to a human.

```
                  compact                              visual
  CSV ──→ LLM Scout ──→ csvplot ──→ LLM Scout ──→ csvplot ──→ Human
          (analysis)     (cheap)    (decides what     (rich)
                                    to show)
```

**Stage 1 — Scout (compact mode)**:
The LLM calls `csvplot summarise -f data.csv --format compact` to cheaply understand the dataset shape: column types, cardinality, distributions, min/max ranges. Based on this, it reasons about which visualizations would be informative — e.g. "the Status column has 3 values, a bar chart would show the distribution; start_date and end_date look like a timeline pair."

The scout may also call `csvplot bubble --format compact` to check sparsity patterns, or `csvplot bar --format compact` to verify a hypothesis about value distributions — all at minimal token cost (55-98% cheaper than visual).

**Stage 2 — Presenter (visual mode)**:
The LLM generates the final `csvplot` commands with `--format visual` (or no `--format` flag) and presents the rendered charts to the human user. The scout stage informed which commands, columns, filters, and options to use.

**Key design point**: compact mode is not a degraded visual — it's a different representation optimized for LLM reasoning. RLE-encoded bars, sparklines, and `●·` matrices carry the same data signal but at a fraction of the token cost. The LLM never needs to "see" the chart; it needs to understand the data.

**MCP integration**: In an MCP (Model Context Protocol) setup, csvplot commands become tools the LLM can invoke. The scout stage maps to tool calls with `--format compact`, and the presenter stage maps to tool calls with `--format visual` whose output is forwarded to the user's terminal.

### Flow 2: UX Tester

A single-stage flow where an LLM evaluates the visual presentation quality of csvplot's output.

```
  CSV ──→ csvplot ──→ LLM UX Tester ──→ Feedback
           (semantic)   (evaluates layout,
                         alignment, readability)
```

**The problem**: An LLM can't parse ANSI escape codes (`\x1b[31m...`), so feeding it `--format visual` output produces garbled input. But `--format compact` changes the representation entirely — the LLM would be reviewing a different UI than what the human sees.

**The solution**: `--format semantic` strips ANSI color codes but preserves the exact visual layout: box-drawing characters (`┌─┐│└─┘`), table alignment, braille chart patterns (`⣿⡇`), whitespace padding — everything that constitutes the visual UX. The LLM sees exactly what a human sees, minus the colors.

**What the UX tester can evaluate**:
- Table column alignment and padding
- Chart proportions and axis labels
- Title placement and truncation behavior
- Whether long values wrap or get cut off
- Overall information density and readability
- Consistency across commands (do all tables look similar?)

**What the UX tester cannot evaluate**:
- Color choices and contrast (stripped by semantic mode)
- ANSI styling (bold, dim, underline)
- Terminal-specific rendering artifacts (font, line height)

### Format Selection Guide

| Scenario | Format | Why |
|----------|--------|-----|
| Human viewing output directly | `visual` | Full colors and Rich formatting |
| LLM analyzing data to decide what to plot | `compact` | 55-98% fewer tokens, data-optimized representation |
| LLM generating charts for human consumption | `visual` | Human sees the real output |
| LLM reviewing visual UX quality | `semantic` | Same layout as visual, parseable by LLM |
| MCP tool call for data exploration | `compact` | Cheap scout calls |
| MCP tool call for final presentation | `visual` | Rich output forwarded to user |
| Automated regression testing of chart output | `semantic` | Stable text output, no ANSI to match against |

### Implementation Details

- **`compact.py`**: Per-command rendering functions (`compact_timeline`, `compact_bar`, `compact_line`, `compact_bubble`, `compact_summarise`). Each takes a spec and produces a self-contained text block with a `[COMPACT:command]` header.
- **`semantic.py`**: Two utilities — `strip_ansi()` (regex removal of `\x1b[...]m` sequences) and `semantic_rich()` (Rich Console capture with `export_text(styles=False)`). Plotext output uses `plt.build()` + `strip_ansi()`; Rich output uses `semantic_rich()`.
- **`renderer.py`**: `render()`, `render_bar()`, `render_line()` accept `build=False` parameter. When `True`, return `plt.build()` string instead of calling `plt.show()`.
- **`cli.py`**: All 5 commands accept `--format visual|compact|semantic` and branch accordingly.
