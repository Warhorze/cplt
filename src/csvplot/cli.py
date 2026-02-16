"""CLI entry point using Typer."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal, Optional, cast

import typer
from rich import print as rprint
from rich.table import Table

from csvplot.bubble import load_bubble_data
from csvplot.completions import complete_column, complete_date_column, complete_where
from csvplot.models import Marker, PlotSpec
from csvplot.reader import (
    load_bar_data,
    load_line_data,
    load_segments,
    parse_datetime,
    parse_where,
)
from csvplot.renderer import render, render_bar, render_line
from csvplot.summarise import summarise_csv

app = typer.Typer(
    name="csvplot",
    no_args_is_help=True,
)


def _validate_format(format_opt: str) -> None:
    """Validate common --format option values."""
    if format_opt not in ("visual", "compact", "semantic"):
        rprint(
            f"[red]Error:[/red] --format must be 'visual', 'compact', or 'semantic', "
            f"got {format_opt!r}"
        )
        raise typer.Exit(1)


def _require_canvas(canvas: str | None) -> str:
    """Ensure a built renderer canvas is available."""
    if canvas is None:
        rprint("[red]Error:[/red] Failed to build semantic output.")
        raise typer.Exit(1)
    return canvas


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
            help="Label segments with this column's value (visual format only)",
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
    where: Annotated[
        Optional[list[str]],
        typer.Option(
            "--where",
            help="Filter rows: COL=value (case-insensitive, repeat for OR/AND)",
            rich_help_panel="Filtering",
        ),
    ] = None,
    where_not: Annotated[
        Optional[list[str]],
        typer.Option(
            "--where-not",
            help="Exclude rows: COL=value (case-insensitive)",
            rich_help_panel="Filtering",
        ),
    ] = None,
    format_opt: Annotated[
        str,
        typer.Option(
            "--format",
            help="Output format: visual, semantic, or compact",
            rich_help_panel="Formatting",
        ),
    ] = "visual",
) -> None:
    """Plot timeline/Gantt-style ranges from a CSV file."""
    _validate_format(format_opt)
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

    # Parse --where / --where-not expressions
    wheres: list[tuple[str, str]] = []
    where_nots: list[tuple[str, str]] = []
    try:
        for expr in where or []:
            wheres.append(parse_where(expr))
        for expr in where_not or []:
            where_nots.append(parse_where(expr))
    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
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
            wheres=wheres or None,
            where_nots=where_nots or None,
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
        color_col_name=color or None,
    )

    # Render
    if format_opt == "compact":
        from csvplot.compact import compact_timeline

        print(compact_timeline(spec))
    elif format_opt == "semantic":
        from csvplot.semantic import strip_ansi

        canvas = _require_canvas(render(spec, build=True))
        print(strip_ansi(canvas))
    else:
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
        typer.Option("--horizontal", help="Use horizontal bars (visual format only)"),
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
    where: Annotated[
        Optional[list[str]],
        typer.Option(
            "--where",
            help="Filter rows: COL=value (case-insensitive)",
            autocompletion=complete_where,
        ),
    ] = None,
    where_not: Annotated[
        Optional[list[str]],
        typer.Option("--where-not", help="Exclude rows: COL=value (case-insensitive)"),
    ] = None,
    format_opt: Annotated[
        str,
        typer.Option("--format", help="Output format: visual, semantic, or compact"),
    ] = "visual",
) -> None:
    """Plot a bar chart of value counts from a CSV column."""
    _validate_format(format_opt)
    if sort not in ("value", "label", "none"):
        rprint(f"[red]Error:[/red] --sort must be 'value', 'label', or 'none', got {sort!r}")
        raise typer.Exit(1)
    sort_by = cast(Literal["value", "label", "none"], sort)

    # Parse --where / --where-not expressions
    wheres: list[tuple[str, str]] = []
    where_nots: list[tuple[str, str]] = []
    try:
        for expr in where or []:
            wheres.append(parse_where(expr))
        for expr in where_not or []:
            where_nots.append(parse_where(expr))
    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    chart_title = title if title else file.stem

    try:
        spec = load_bar_data(
            path=file,
            column=column,
            sort_by=sort_by,
            top=top,
            max_rows=head,
            title=chart_title,
            horizontal=horizontal,
            wheres=wheres or None,
            where_nots=where_nots or None,
        )
    except KeyError as e:
        rprint(f"[red]Error:[/red] Column not found in CSV: {e}")
        raise typer.Exit(1)

    if not spec.labels:
        rprint("[yellow]Warning:[/yellow] No data found in the column.")
        raise typer.Exit(0)

    if format_opt == "compact":
        from csvplot.compact import compact_bar

        print(compact_bar(spec))
    elif format_opt == "semantic":
        from csvplot.semantic import strip_ansi

        canvas = _require_canvas(render_bar(spec, build=True))
        print(strip_ansi(canvas))
    else:
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
    where: Annotated[
        Optional[list[str]],
        typer.Option(
            "--where",
            help="Filter rows: COL=value (case-insensitive)",
            autocompletion=complete_where,
        ),
    ] = None,
    where_not: Annotated[
        Optional[list[str]],
        typer.Option("--where-not", help="Exclude rows: COL=value (case-insensitive)"),
    ] = None,
    format_opt: Annotated[
        str,
        typer.Option("--format", help="Output format: visual, semantic, or compact"),
    ] = "visual",
) -> None:
    """Plot a line chart from CSV columns."""
    _validate_format(format_opt)
    if len(y) < 1:
        rprint("[red]Error:[/red] --y requires at least 1 value.")
        raise typer.Exit(1)

    # Parse --where / --where-not expressions
    wheres: list[tuple[str, str]] = []
    where_nots: list[tuple[str, str]] = []
    try:
        for expr in where or []:
            wheres.append(parse_where(expr))
        for expr in where_not or []:
            where_nots.append(parse_where(expr))
    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
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
            wheres=wheres or None,
            where_nots=where_nots or None,
        )
    except KeyError as e:
        rprint(f"[red]Error:[/red] Column not found in CSV: {e}")
        raise typer.Exit(1)

    if not spec.x_values:
        rprint("[yellow]Warning:[/yellow] No data found.")
        raise typer.Exit(0)

    if format_opt == "compact":
        from csvplot.compact import compact_line

        print(compact_line(spec))
    elif format_opt == "semantic":
        from csvplot.semantic import strip_ansi

        canvas = _require_canvas(render_line(spec, build=True))
        print(strip_ansi(canvas))
    else:
        render_line(spec)


@app.command()
def summarise(
    file: Annotated[
        Path,
        typer.Option("--file", "-f", help="Path to CSV file", exists=True, dir_okay=False),
    ],
    head: Annotated[
        Optional[int],
        typer.Option("--head", min=1, help="Only read the first N CSV rows"),
    ] = None,
    sample: Annotated[
        Optional[int],
        typer.Option("--sample", min=1, help="Show N random sample rows as preview"),
    ] = None,
    where: Annotated[
        Optional[list[str]],
        typer.Option(
            "--where",
            help="Filter rows: COL=value (case-insensitive)",
            autocompletion=complete_where,
        ),
    ] = None,
    where_not: Annotated[
        Optional[list[str]],
        typer.Option("--where-not", help="Exclude rows: COL=value (case-insensitive)"),
    ] = None,
    format_opt: Annotated[
        str,
        typer.Option("--format", help="Output format: visual, semantic, or compact"),
    ] = "visual",
) -> None:
    """Print a summary of a CSV file — column types, counts, nulls, top values."""
    _validate_format(format_opt)
    sample_rows: list[dict[str, str]] = []
    # Parse --where / --where-not expressions
    wheres: list[tuple[str, str]] = []
    where_nots: list[tuple[str, str]] = []
    try:
        for expr in where or []:
            wheres.append(parse_where(expr))
        for expr in where_not or []:
            where_nots.append(parse_where(expr))
    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    try:
        if sample:
            summaries, sample_rows = summarise_csv(
                path=file,
                wheres=wheres or None,
                where_nots=where_nots or None,
                max_rows=head,
                sample_n=sample,
                return_sample=True,
            )
        else:
            summaries = summarise_csv(
                path=file,
                wheres=wheres or None,
                where_nots=where_nots or None,
                max_rows=head,
            )
    except KeyError as e:
        rprint(f"[red]Error:[/red] Column not found in CSV: {e}")
        raise typer.Exit(1)

    if not summaries:
        rprint("[yellow]Warning:[/yellow] No columns found in CSV.")
        raise typer.Exit(0)

    if format_opt == "compact":
        from csvplot.compact import compact_summarise

        print(compact_summarise(summaries, title=file.name, sample_rows=sample_rows or None))
    else:
        # Build summary table
        table = Table(title=f"Summary: {file.name}")
        table.add_column("Column", style="bold")
        table.add_column("Type")
        table.add_column("Rows", justify="right")
        table.add_column("Non-null", justify="right")
        table.add_column("Unique", justify="right")
        table.add_column("Min")
        table.add_column("Max")
        table.add_column("Top Values (freq)")

        for s in summaries:
            top_str = ""
            if s.high_cardinality:
                top_str = "[dim]>10K unique[/dim]"
            elif s.top_values:
                top_str = ", ".join(f"{v}({c})" for v, c in s.top_values[:5])

            table.add_row(
                s.name,
                s.detected_type,
                str(s.row_count),
                str(s.non_null_count),
                str(s.unique_count),
                s.min_val or "-",
                s.max_val or "-",
                top_str or "-",
            )

        # Build sample table if requested
        sample_table = None
        if sample_rows:
            sample_table = Table(title=f"Sample ({len(sample_rows)} random rows)")
            cols = list(sample_rows[0].keys())
            for col in cols:
                sample_table.add_column(col)
            for row in sample_rows:
                sample_table.add_row(*(row[c] for c in cols))

        if format_opt == "semantic":
            from csvplot.semantic import semantic_rich

            renderables = [table]
            if sample_table:
                renderables.append(sample_table)
            print(semantic_rich(*renderables), end="")
        else:
            rprint(table)
            if sample_table:
                rprint()
                rprint(sample_table)


@app.command()
def bubble(
    file: Annotated[
        Path,
        typer.Option("--file", "-f", help="Path to CSV file", exists=True, dir_okay=False),
    ],
    cols: Annotated[
        list[str],
        typer.Option(
            "--cols",
            help="Columns to check for presence/absence",
            autocompletion=complete_column,
        ),
    ],
    y: Annotated[
        str,
        typer.Option(
            "--y",
            help="Row label column",
            autocompletion=complete_column,
        ),
    ],
    color: Annotated[
        Optional[str],
        typer.Option(
            "--color",
            help="Color rows by this column",
            autocompletion=complete_column,
        ),
    ] = None,
    top: Annotated[
        Optional[int],
        typer.Option("--top", min=1, help="Show only top N columns by fill-rate"),
    ] = None,
    head: Annotated[
        Optional[int],
        typer.Option("--head", min=1, help="Only read the first N CSV rows"),
    ] = None,
    title: Annotated[
        Optional[str],
        typer.Option("--title", help="Chart title (defaults to filename)"),
    ] = None,
    where: Annotated[
        Optional[list[str]],
        typer.Option(
            "--where",
            help="Filter rows: COL=value (case-insensitive)",
            autocompletion=complete_where,
        ),
    ] = None,
    where_not: Annotated[
        Optional[list[str]],
        typer.Option("--where-not", help="Exclude rows: COL=value (case-insensitive)"),
    ] = None,
    format_opt: Annotated[
        str,
        typer.Option("--format", help="Output format: visual, semantic, or compact"),
    ] = "visual",
) -> None:
    """Plot a presence/absence dot matrix from CSV columns."""
    _validate_format(format_opt)
    if not cols:
        rprint("[red]Error:[/red] --cols requires at least 1 column.")
        raise typer.Exit(1)

    # Parse --where / --where-not expressions
    wheres: list[tuple[str, str]] = []
    where_nots: list[tuple[str, str]] = []
    try:
        for expr in where or []:
            wheres.append(parse_where(expr))
        for expr in where_not or []:
            where_nots.append(parse_where(expr))
    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    try:
        spec = load_bubble_data(
            path=file,
            cols=cols,
            y_col=y,
            color_col=color,
            max_rows=head,
            top=top,
            wheres=wheres or None,
            where_nots=where_nots or None,
        )
    except KeyError as e:
        rprint(f"[red]Error:[/red] Column not found in CSV: {e}")
        raise typer.Exit(1)

    if not spec.y_labels:
        rprint("[yellow]Warning:[/yellow] No data found.")
        raise typer.Exit(0)

    chart_title = title if title else file.stem

    if format_opt == "compact":
        from csvplot.compact import compact_bubble

        print(compact_bubble(spec, title=chart_title))
    else:
        palette = [
            "red",
            "green",
            "yellow",
            "blue",
            "magenta",
            "cyan",
            "bright_red",
            "bright_green",
            "bright_yellow",
            "bright_blue",
            "bright_magenta",
            "bright_cyan",
        ]
        color_map: dict[str, str] = {}
        legend_table: Table | None = None
        if color and spec.color_keys:
            unique_keys: list[str] = []
            seen_keys: set[str] = set()
            for key in spec.color_keys:
                if key not in seen_keys:
                    unique_keys.append(key)
                    seen_keys.add(key)
            color_map = {key: palette[i % len(palette)] for i, key in enumerate(unique_keys)}
            legend_table = Table(title="Legend")
            legend_table.add_column("Color", justify="center")
            legend_table.add_column(color)
            for key in unique_keys:
                style = color_map[key]
                legend_table.add_row(f"[{style}]●[/{style}]", key)

        # Build Rich table with Unicode dots
        table = Table(title=chart_title)
        table.add_column("", style="bold")  # y-label column
        for col_name in spec.col_names:
            table.add_column(col_name, justify="center")

        for row_idx, label in enumerate(spec.y_labels):
            row_style = (
                color_map.get(spec.color_keys[row_idx], "")
                if color_map and row_idx < len(spec.color_keys)
                else ""
            )
            label_cell = f"[{row_style}]{label}[/{row_style}]" if row_style else label
            cells = []
            for val in spec.matrix[row_idx]:
                if val:
                    cells.append(f"[{row_style}]●[/{row_style}]" if row_style else "[green]●[/green]")
                else:
                    cells.append("")
            table.add_row(label_cell, *cells)

        if format_opt == "semantic":
            from csvplot.semantic import semantic_rich

            if legend_table:
                print(semantic_rich(table, legend_table), end="")
            else:
                print(semantic_rich(table), end="")
        else:
            rprint(table)
            if legend_table:
                rprint()
                rprint(legend_table)
