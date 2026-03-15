# Changelog

## 0.1.0 — Initial Release

### Commands

- **timeline** — Gantt-style date-range charts with layered start/end pairs, `--y-detail` sub-grouping, `--vline`/`--label` reference lines, and `--dot` per-row date markers
- **bar** — Value-count bar charts with `--sort`, `--top`, `--horizontal`, `--labels`, and per-category palette colours
- **line** — Numeric and date-indexed line charts with `--from`/`--to` date filtering
- **bubble** — Presence/absence dot matrix with `--sort`, `--transpose`, `--group-by` aggregation, `--encode` auto-encoding, `--sample`, `--top`, `--color` row styling, and fill-rate summary footer
- **summarise** — CSV profiling: column types, null counts, top values with frequencies, plus data-quality stats (null sentinels, zeros, mean/stddev, date formats, whitespace issues)

### Output formats

- **visual** — Full-colour terminal charts via plotext (timeline, bar, line) and Rich tables (bubble, summarise)
- **compact** — Token-efficient ASCII renderers with RLE encoding, designed for LLM consumption
- **semantic** — ANSI-stripped plain-text capture for accessibility and diffing

### Export

- `--export <path>.png` on all five commands — renders ANSI terminal output to PNG with braille dot rendering and supersampled anti-aliasing

### Filtering

- `--where COL=value` and `--where-not COL=value` on all commands with case-insensitive matching
- `--head N` to limit input rows

### Shell integration

- Context-aware tab completion for `--where` values (column names, then `COL=value` pairs)
- Completion for CSV file paths with tilde expansion

### Developer tooling

- CLI smoke test script (`scripts/run_cli_smoke.sh`)
- Design review image generator (`scripts/generate_design_review_images.sh`)
- Animated demo GIF recorder via VHS (`scripts/generate_demos.sh`)
- CLI docs generator (`scripts/generate_cli_docs.sh`)
- MkDocs documentation site
- UX test suite with combination matrix coverage
- "Ready for Release" checklist in DEVELOPERS.md

## v0.4.0 (2026-03-15)

### Feat

- **cli**: add hist command
- **compact**: add compact_hist sparkline output
- **renderer**: add render_hist for plotext histogram
- **reader**: add load_hist_data for histogram binning
- **models**: add HistSpec dataclass
- **theme**: add unified RAINBOW_PALETTE module

### Refactor

- **theme**: unify color palettes across renderer, bubble, and summarise

## v0.3.1 (2026-03-15)

### Refactor

- **summarise**: polish distribution, docs, and README (#6)

## v0.3.0 (2026-03-15)

### Feat

- smarter summarise with category threshold, histograms & ID detection (#4)

### Fix

- **ci**: replace mypy with pyright in typecheck job

## v0.2.0 (2026-03-14)

### Feat

- **cli**: add --export PNG option to all 5 commands
- **export**: add ANSI → PNG renderer with braille support
- **compact**: display data-quality stats in compact summarise output
- **cli**: display data-quality stats in summarise output
- **summarise**: add null sentinels, zeros, mean/stddev, date formats, whitespace tracking
- **demos**: add --help, subcommand tab, per-dir paths, --where discovery
- **demos**: slower typing and smoother tab in lib.sh
- **demos**: add column discovery menus and tab completion to sim scripts
- **bar**: cycle PALETTE colors for distinct bar chart colors
- **bubble**: refactor pipeline — merge group-by, col=value encode, auto-cap
- **bubble**: add --transpose flag to swap rows and columns
- **bubble**: add --group-by aggregation mode
- **bubble**: add summary footer row with per-column fill rates
- **bubble**: add --sort option for row ordering
- **bubble**: remove auto-cap and add truncation footer
- **cli**: wire --dot option into timeline command
- **renderer**: render dots as scatter points on timeline
- **compact**: render dots as ◆ overlaid on timeline rows
- **reader**: add load_dots() for per-row single-date points
- **models**: add Dot dataclass and PlotSpec.dots/dot_col_names fields
- **cli**: wire autocompletion=complete_where on all --where-not and timeline --where
- complete priority 2 ux follow-up tasks
- **bubble**: add --sample and auto-truncate large visual output
- **images**: render ansi colors in generated png artifacts
- **pipeline**: switch generated chart artifacts to png
- **summarise**: rename Top Values header to include freq legend
- **reader**: warn on stderr when rows have unparseable dates
- **semantic**: add ANSI-stripping semantic format for Rich output
- **renderer**: add build mode to return canvas string instead of printing
- **cli**: add --format compact option to all commands
- **compact**: add compact output module with RLE-encoded ASCII renderers
- **filter**: add case-insensitive column name resolution in --where
- **completions**: add context-aware --where value completion
- **cli**: add bubble matrix command with Rich table rendering
- **cli**: add summarise command with type detection and sample preview
- **filter**: add --where and --where-not filtering to all commands
- **cli**: add bar and line commands, --y-detail, --from/--to, --title
- **renderer**: add bar/line renderers, improve color mapping and legends
- **reader**: add bar/line data loaders, y-detail, and numeric detection
- **models**: add BarSpec, LineSpec and row_index to Segment

### Fix

- **completions**: prevent extra space after --where COL= tab completion
- **scripts**: rename --marker flags to --vline/--label in readme image gen
- **bar**: apply --top before label sorting
- **completions**: patch Typer bash script to handle COMP_WORDBREAKS '='
- **completions**: stage-1 returns COL= only; where-context for --where-not
- improve column errors and empty where UX
- **renderer**: improve multi-layer timeline label and legend clarity
- **bubble**: show row numbers only when labels truncate
- **reader**: raise clear error for malformed CSV rows
- **completions**: resolve tilde paths for CSV autocompletion
- **bubble**: apply --color row styling and legend in visual output
- switch to pyright and harden state handling
- **compact**: round line min/max to 4 significant figures
- **reader**: drop invalid date rows in line chart date mode
- **reader**: skip open-end replacement for invalid non-empty end dates

### Refactor

- rename package csvplot → cplt
- **scripts**: use --export instead of external PNG renderer
- **models**: rename Marker→VLine, --marker→--vline, --marker-label→--label
