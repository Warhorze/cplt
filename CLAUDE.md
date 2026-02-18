# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is csvplot?

A CLI tool for plotting and summarising CSV data in the terminal. Supports timeline/Gantt ranges, bar charts, line charts, bubble matrices, and CSV summaries. Uses stdlib `csv` (no pandas), Typer for CLI, plotext for charts, and Rich for table formatting.

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
- **When manually testing CLI output**, always use `--format compact` instead of the default visual plotext output. The compact format is token-efficient and readable by LLMs.

## Git conventions

- Use nano (small, atomic) commits with conventional commit messages
- Format: `type(scope): description` (e.g., `feat(cli): add --title option`)
- Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

## Architecture

Data flows linearly: **CLI args → reader → PlotSpec → renderer → terminal**

See `docs/architecture.md` for full module layout and behavior contracts. Key points for working in this codebase:

- `cli.py` — Typer commands + arg validation. Entry point for all commands.
- `reader.py` / `bubble.py` / `summarise.py` — CSV loading per command type.
- `models.py` — Dataclasses for plot specs.
- `renderer.py` / `compact.py` / `semantic.py` — One renderer per `--format` mode.
- `completions.py` — Shell completion for columns/values.

## Key design details

- `--x` takes a flat list of column names that must be even-length; they're chunked into start/end pairs to form layers (layer 0, layer 1, etc.)
- Multiple `--y` values are concatenated with ` | ` to form composite y-labels (flat, not hierarchical)
- Bubble uses `--cols` (not `--x`) as the primary matrix-column option.
- Ruff config: line-length 100, target Python 3.11, rules E/F/I
