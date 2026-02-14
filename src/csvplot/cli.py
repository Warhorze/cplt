"""CLI entry point using Typer."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich import print as rprint

from csvplot.completions import complete_column, complete_date_column
from csvplot.models import Marker, PlotSpec
from csvplot.reader import load_bar_data, load_line_data, load_segments, parse_datetime
from csvplot.renderer import render, render_bar, render_line

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
            help=(
                "Time-range columns as start/end pairs. Example: --x START --x END for one layer, "
                "--x S1 --x E1 --x S2 --x E2 for two layers"
            ),
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
    y_detail: Annotated[
        Optional[str],
        typer.Option(
            "--y-detail",
            help="Sub-group within --y by appending this column's value",
            autocompletion=complete_column,
            rich_help_panel="Formatting",
        ),
    ] = None,
    head: Annotated[
        Optional[int],
        typer.Option(
            "--head",
            min=1,
            help="Only read the first N CSV rows",
            rich_help_panel="Filtering",
        ),
    ] = None,
    view_from: Annotated[
        Optional[str],
        typer.Option(
            "--from",
            help="Zoom start date (YYYY-MM-DD), only show data from this date",
            rich_help_panel="Filtering",
        ),
    ] = None,
    view_to: Annotated[
        Optional[str],
        typer.Option(
            "--to",
            help="Zoom end date (YYYY-MM-DD), only show data up to this date",
            rich_help_panel="Filtering",
        ),
    ] = None,
    title: Annotated[
        Optional[str],
        typer.Option(
            "--title",
            help="Chart title (defaults to filename)",
            rich_help_panel="Formatting",
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
            y_detail_col=y_detail,
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

    # Warn if --marker-label is given without --marker
    if marker_label and not marker:
        rprint("[yellow]Warning:[/yellow] --marker-label has no effect without --marker.")

    # Build PlotSpec
    markers: list[Marker] = []
    if marker:
        marker_dt = parse_datetime(marker)
        if marker_dt is None:
            rprint(f"[red]Error:[/red] Could not parse --marker date: {marker}")
            raise typer.Exit(1)
        markers.append(Marker(date=marker_dt, label=marker_label or ""))

    # Parse --from / --to view window
    view_start = None
    view_end = None
    if view_from:
        view_start = parse_datetime(view_from)
        if view_start is None:
            rprint(f"[red]Error:[/red] Could not parse --from date: {view_from}")
            raise typer.Exit(1)
    if view_to:
        view_end = parse_datetime(view_to)
        if view_end is None:
            rprint(f"[red]Error:[/red] Could not parse --to date: {view_to}")
            raise typer.Exit(1)

    # Determine chart title
    chart_title = title if title else file.stem

    spec = PlotSpec(
        segments=segments,
        markers=markers,
        view_start=view_start,
        view_end=view_end,
        title=chart_title,
        x_pair_names=x_pairs,
        color_col_name=color or "",
    )

    # Render
    render(spec)


@app.command()
def bar(
    file: Annotated[
        Path,
        typer.Option("--file", "-f", help="Path to CSV file", exists=True, dir_okay=False),
    ],
    column: Annotated[
        str,
        typer.Option(
            "--column",
            "-c",
            help="Column to count values of",
            autocompletion=complete_column,
        ),
    ],
    sort: Annotated[
        str,
        typer.Option(
            "--sort",
            help="Sort by: value (desc count), label (alpha), none (CSV order)",
        ),
    ] = "value",
    horizontal: Annotated[
        bool,
        typer.Option("--horizontal", help="Use horizontal bars"),
    ] = False,
    top: Annotated[
        Optional[int],
        typer.Option("--top", min=1, help="Show only the top N categories"),
    ] = None,
    head: Annotated[
        Optional[int],
        typer.Option("--head", min=1, help="Only read the first N CSV rows"),
    ] = None,
    title: Annotated[
        Optional[str],
        typer.Option("--title", help="Chart title (defaults to filename)"),
    ] = None,
) -> None:
    """Plot a bar chart of value counts from a CSV column."""
    if sort not in ("value", "label", "none"):
        rprint(f"[red]Error:[/red] --sort must be 'value', 'label', or 'none', got {sort!r}")
        raise typer.Exit(1)

    chart_title = title if title else file.stem

    try:
        spec = load_bar_data(
            path=file,
            column=column,
            sort_by=sort,
            top=top,
            max_rows=head,
            title=chart_title,
            horizontal=horizontal,
        )
    except KeyError as e:
        rprint(f"[red]Error:[/red] Column not found in CSV: {e}")
        raise typer.Exit(1)

    if not spec.labels:
        rprint("[yellow]Warning:[/yellow] No data found in the column.")
        raise typer.Exit(0)

    render_bar(spec)


@app.command()
def line(
    file: Annotated[
        Path,
        typer.Option("--file", "-f", help="Path to CSV file", exists=True, dir_okay=False),
    ],
    x: Annotated[
        str,
        typer.Option(
            "--x",
            help="X-axis column (date or sequential)",
            autocompletion=complete_column,
        ),
    ],
    y: Annotated[
        list[str],
        typer.Option(
            "--y",
            help="Y-axis column(s) (numeric); repeat for multiple lines",
            autocompletion=complete_column,
        ),
    ],
    color: Annotated[
        Optional[str],
        typer.Option(
            "--color",
            help="Group into separate lines by this column",
            autocompletion=complete_column,
        ),
    ] = None,
    head: Annotated[
        Optional[int],
        typer.Option("--head", min=1, help="Only read the first N CSV rows"),
    ] = None,
    title: Annotated[
        Optional[str],
        typer.Option("--title", help="Chart title (defaults to filename)"),
    ] = None,
) -> None:
    """Plot a line chart from CSV columns."""
    if len(y) < 1:
        rprint("[red]Error:[/red] --y requires at least 1 value.")
        raise typer.Exit(1)

    chart_title = title if title else file.stem

    try:
        spec = load_line_data(
            path=file,
            x_col=x,
            y_cols=y,
            color_col=color,
            max_rows=head,
            title=chart_title,
        )
    except KeyError as e:
        rprint(f"[red]Error:[/red] Column not found in CSV: {e}")
        raise typer.Exit(1)

    if not spec.x_values:
        rprint("[yellow]Warning:[/yellow] No data found.")
        raise typer.Exit(0)

    render_line(spec)
