"""CLI entry point using Typer."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import print as rprint

from csvplot.completions import complete_column, complete_date_column
from csvplot.models import Marker, PlotSpec
from csvplot.reader import load_segments, parse_datetime
from csvplot.renderer import render

app = typer.Typer(
    name="csvplot",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Plot data from CSV files directly in the terminal."""


@app.command()
def timeline(
    file: Annotated[
        Path,
        typer.Option("--file", "-f", help="Path to CSV file", exists=True, dir_okay=False),
    ],
    x: Annotated[
        list[str],
        typer.Option(
            "--x",
            help="Time-range columns as start/end pairs (--x START --x END, repeat for layers)",
            autocompletion=complete_date_column,
        ),
    ],
    y: Annotated[
        list[str],
        typer.Option(
            "--y",
            help="Categorical Y-axis column(s); repeat to combine",
            autocompletion=complete_column,
        ),
    ],
    color: Annotated[
        Optional[str],
        typer.Option(
            "--color",
            help="Color rows by this column",
            autocompletion=complete_column,
            rich_help_panel="Formatting",
        ),
    ] = None,
    txt: Annotated[
        Optional[str],
        typer.Option(
            "--txt",
            help="Label segments with this column's value",
            autocompletion=complete_column,
            rich_help_panel="Formatting",
        ),
    ] = None,
    marker: Annotated[
        Optional[str],
        typer.Option(
            "--marker",
            help="Vertical marker date (YYYY-MM-DD)",
            rich_help_panel="Formatting",
        ),
    ] = None,
    marker_label: Annotated[
        Optional[str],
        typer.Option(
            "--marker-label",
            help="Label for the marker line",
            rich_help_panel="Formatting",
        ),
    ] = None,
    open_end: Annotated[
        bool,
        typer.Option(
            "--open-end/--no-open-end",
            help="Replace NULL/sentinel end dates with today",
            rich_help_panel="Formatting",
        ),
    ] = True,
    head: Annotated[
        Optional[int],
        typer.Option(
            "--head",
            min=1,
            help="Only read the first N CSV rows",
            rich_help_panel="Filtering",
        ),
    ] = None,
) -> None:
    """Plot timeline/Gantt-style ranges from a CSV file."""
    # Validate --x: need at least 2 values, and an even count
    if len(x) < 2:
        rprint("[red]Error:[/red] --x requires at least 2 values (start and end columns).")
        raise typer.Exit(1)
    if len(x) % 2 != 0:
        rprint("[red]Error:[/red] --x requires an even number of values (start/end pairs).")
        raise typer.Exit(1)
    if len(y) < 1:
        rprint("[red]Error:[/red] --y requires at least 1 value.")
        raise typer.Exit(1)

    # Chunk --x values into pairs
    x_pairs = [(x[i], x[i + 1]) for i in range(0, len(x), 2)]

    # Determine open-end replacement date
    open_end_dt = datetime.now(tz=timezone.utc).replace(tzinfo=None) if open_end else None

    # Load segments
    try:
        segments = load_segments(
            path=file,
            x_pairs=x_pairs,
            y_col=y,
            color_col=color,
            txt_col=txt,
            open_end=open_end_dt,
            max_rows=head,
        )
    except KeyError as e:
        rprint(f"[red]Error:[/red] Column not found in CSV: {e}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Error:[/red] Failed to read CSV: {e}")
        raise typer.Exit(1)

    if not segments:
        rprint("[yellow]Warning:[/yellow] No valid segments found in the data.")
        raise typer.Exit(0)

    # Build PlotSpec
    markers: list[Marker] = []
    if marker:
        marker_dt = parse_datetime(marker)
        if marker_dt is None:
            rprint(f"[red]Error:[/red] Could not parse --marker date: {marker}")
            raise typer.Exit(1)
        markers.append(Marker(date=marker_dt, label=marker_label or ""))

    spec = PlotSpec(segments=segments, markers=markers)

    # Render
    render(spec)
