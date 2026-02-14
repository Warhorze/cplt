# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is csvplot?

A CLI tool for plotting timeline/Gantt-style range charts from CSV files in the terminal. Uses stdlib `csv` (no pandas), Typer for CLI, plotext for rendering, and Rich for terminal formatting.

## Commands

```bash
uv sync --extra dev          # install with dev deps (pytest, ruff, mypy)
uv run pytest                # run all tests
uv run pytest tests/test_reader.py # run a single test file
uv run pytest -k "test_name" # run a single test by name
uv run ruff check src/ tests/  # lint
uv run ruff format src/ tests/ # format
```

## Development workflow

- **ALWAYS use red/green (TDD) development**: write a failing test first, then write the minimal code to make it pass, then refactor. No production code without a failing test driving it.

## Git conventions

- Use nano (small, atomic) commits with conventional commit messages
- Format: `type(scope): description` (e.g., `feat(cli): add --title option`)
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

## Architecture

Data flows linearly: **CLI args → reader → PlotSpec → renderer → terminal**

- `cli.py` — Typer app with a single `timeline` command. Validates `--x` pairs, builds a `PlotSpec`, calls `render()`. Column-name options use autocompletion callbacks from `completions.py`.
- `reader.py` — `load_segments()` reads CSV via `csv.DictReader` and emits `Segment` objects. `parse_datetime()` tries multiple `strptime` formats. Sentinel dates (year 9999) and empty values return `None`. Open-ended ranges get replaced with today's date by default.
- `models.py` — Frozen dataclasses: `Segment` (one time range per row per layer), `Marker` (vertical date line), `PlotSpec` (full render specification).
- `renderer.py` — Converts `PlotSpec` into plotext calls. Each segment is `plt.plot([start, end], [y, y])`. Supports multiple layers (different x-pair columns) offset vertically within a y-group, color mapping by column or auto by y-label, and sub-row assignment so multiple CSV rows with the same y-label get separate lines.
- `completions.py` — Tab-completion callbacks cached by `(path, mtime)`. `--x` suggests only datetime columns with smart start/end keyword ordering based on position.

## Key design details

- `--x` takes a flat list of column names that must be even-length; they're chunked into start/end pairs to form layers (layer 0, layer 1, etc.)
- Multiple `--y` values are concatenated with ` | ` to form composite y-labels (flat, not hierarchical)
- Ruff config: line-length 100, target Python 3.11, rules E/F/I
