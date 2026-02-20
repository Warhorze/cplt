# csvplot

[![PyPI](https://img.shields.io/pypi/v/csvplot)](https://pypi.org/project/csvplot/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/Warhorze/csvplot/actions/workflows/ci.yml/badge.svg)](https://github.com/Warhorze/csvplot/actions/workflows/ci.yml)

Plot CSV files directly in your terminal.
Zero GUI. Zero notebooks. Just your CLI.

## Why csvplot

Most terminal plotting tools handle bars and lines, but not timeline ranges from CSV start/end columns. `csvplot` focuses on that workflow while still covering the common chart types:

- `timeline` for Gantt-style range plots
- `bar` for value-count distribution
- `line` for numeric trends over time or sequence
- `bubble` for presence/absence matrices
- `summarise` for fast column profiling

## Get Started In 30 Seconds

```bash
pip install csvplot
csvplot timeline -f data/projects.csv --x planned_start --x planned_end --y project
```

## Install

```bash
pip install csvplot
# or
pipx install csvplot
```

Standalone binaries are available from the [latest GitHub release](https://github.com/Warhorze/csvplot/releases/latest).

Enable shell completion after install:

```bash
csvplot --install-completion
```

## What It Looks Like

Every demo starts with `--help` so you can see all available flags, then builds a command using tab completion to discover columns and values.

### Timeline / Gantt

Visualise project schedules as Gantt-style ranges with color-coded status and a "today" marker.

![Timeline chart output](assets/images/timeline.gif)

### Bar Chart

Count values in a column, filter with `--where`, and label the bars. Watch tab completion discover columns and filter values.

![Bar chart output](assets/images/bar.gif)

### Line Chart

Plot numeric trends over time with `--head` to limit rows and `--title` for context.

![Line chart output](assets/images/line.gif)

### Bubble Matrix

Spot missing data patterns across columns. Rows are labeled, columns are presence/absence dots, colored by group.

![Bubble matrix output](assets/images/bubble.gif)

### Summarise

Quick column profiling — types, nulls, uniques, and top values at a glance.

![Summarise output](assets/images/summarise.gif)

### Tab Completion

Deep completion for `--where` filters: discover available columns, then see matching values.

![Tab completion options](assets/images/completion.gif)

## Quick Start

```bash
# 1) inspect columns and data quality
csvplot summarise -f data/projects.csv

# 2) make your first timeline
csvplot timeline -f data/projects.csv --x planned_start --x planned_end --y project

# 3) filter rows
csvplot bar -f data/titanic.csv -c Embarked --where "Sex=female"
```

## Output Modes

All plotting and summary commands support `--format`:

- `visual` (default): full Rich/plotext terminal visuals
- `semantic`: ANSI-stripped visual output (useful for LLM UX inspection)
- `compact`: token-efficient output for LLM analysis pipelines

Example:

```bash
csvplot bar -f data/titanic.csv -c Sex --format compact
```

## Docs

- CLI reference: `docs/cli.md`
- Project docs: `docs/`

## For Contributors

Developer-only workflows (UX review loop, artifact generation, docs tooling, tests) live in `DEVELOPERS.md`.

## License

[MIT](LICENSE)
