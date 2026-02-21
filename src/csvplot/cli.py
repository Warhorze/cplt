"""CLI entry point using Typer."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal, Optional, cast

import typer
from rich import print as rprint
from rich.table import Table

from csvplot.bubble import GroupedBubbleSpec, load_bubble_data
from csvplot.completions import complete_column, complete_date_column, complete_where
from csvplot.models import Dot, PlotSpec, VLine
from csvplot.reader import (
    load_bar_data,
    load_dots,
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


def _format_key_error(exc: KeyError) -> str:
    """Return a readable KeyError message without Python repr noise."""
    if exc.args:
        return str(exc.args[0])
    return str(exc)


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
        str | None,
        typer.Option(
            "--color",
            help="Color rows by this column",
            autocompletion=complete_column,
            rich_help_panel="Formatting",
        ),
    ] = None,
    txt: Annotated[
        str | None,
        typer.Option(
            "--txt",
            help="Label segments with this column's value (visual format only)",
            autocompletion=complete_column,
            rich_help_panel="Formatting",
        ),
    ] = None,
    vline: Annotated[
        str | None,
        typer.Option(
            "--vline",
            help="Vertical reference line date (YYYY-MM-DD)",
            rich_help_panel="Formatting",
        ),
    ] = None,
    label: Annotated[
        str | None,
        typer.Option(
            "--label",
            help="Label for the vertical reference line",
            rich_help_panel="Formatting",
        ),
    ] = None,
    dot: Annotated[
        Optional[list[str]],
        typer.Option(
            "--dot",
            help="Date column(s) to render as per-row dot markers",
            autocompletion=complete_date_column,
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
        str | None,
        typer.Option(
            "--y-detail",
            help="Sub-group within --y by appending this column's value",
            autocompletion=complete_column,
            rich_help_panel="Formatting",
        ),
    ] = None,
    head: Annotated[
        int | None,
        typer.Option(
            "--head",
            min=1,
            help="Only read the first N CSV rows",
            rich_help_panel="Filtering",
        ),
    ] = None,
    view_from: Annotated[
        str | None,
        typer.Option(
            "--from",
            help="Zoom start date (YYYY-MM-DD), only show data from this date",
            rich_help_panel="Filtering",
        ),
    ] = None,
    view_to: Annotated[
        str | None,
        typer.Option(
            "--to",
            help="Zoom end date (YYYY-MM-DD), only show data up to this date",
            rich_help_panel="Filtering",
        ),
    ] = None,
    title: Annotated[
        str | None,
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
            autocompletion=complete_where,
            rich_help_panel="Filtering",
        ),
    ] = None,
    where_not: Annotated[
        Optional[list[str]],
        typer.Option(
            "--where-not",
            help="Exclude rows: COL=value (case-insensitive)",
            autocompletion=complete_where,
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
        rprint(f"[red]Error:[/red] {_format_key_error(e)}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Error:[/red] Failed to read CSV: {e}")
        raise typer.Exit(1)

    if not segments:
        rprint("[yellow]Warning:[/yellow] No valid segments found in the data.")
        raise typer.Exit(0)

    # Warn if --label is given without --vline
    if label and not vline:
        rprint("[yellow]Warning:[/yellow] --label has no effect without --vline.")

    # Build PlotSpec
    vlines: list[VLine] = []
    if vline:
        vline_dt = parse_datetime(vline)
        if vline_dt is None:
            rprint(f"[red]Error:[/red] Could not parse --vline date: {vline}")
            raise typer.Exit(1)
        vlines.append(VLine(date=vline_dt, label=label or ""))

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

    # Load dots
    dot_cols = dot or []
    dots: list[Dot] = []
    if dot_cols:
        try:
            dots = load_dots(
                path=file,
                dot_cols=dot_cols,
                y_col=y,
                color_col=color,
                max_rows=head,
                wheres=wheres or None,
                where_nots=where_nots or None,
            )
        except KeyError as e:
            rprint(f"[red]Error:[/red] {_format_key_error(e)}")
            raise typer.Exit(1)

    # Determine chart title
    chart_title = title if title else file.stem

    spec = PlotSpec(
        segments=segments,
        vlines=vlines,
        view_start=view_start,
        view_end=view_end,
        title=chart_title,
        x_pair_names=x_pairs,
        color_col_name=color or None,
        dots=dots,
        dot_col_names=dot_cols,
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
    labels: Annotated[
        bool,
        typer.Option("--labels", help="Show exact values on bars (visual format only)"),
    ] = False,
    top: Annotated[
        int | None,
        typer.Option("--top", min=1, help="Show only the top N categories"),
    ] = None,
    head: Annotated[
        int | None,
        typer.Option("--head", min=1, help="Only read the first N CSV rows"),
    ] = None,
    title: Annotated[
        str | None,
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
        typer.Option(
            "--where-not",
            help="Exclude rows: COL=value (case-insensitive)",
            autocompletion=complete_where,
        ),
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
            show_labels=labels,
            wheres=wheres or None,
            where_nots=where_nots or None,
        )
    except KeyError as e:
        rprint(f"[red]Error:[/red] {_format_key_error(e)}")
        raise typer.Exit(1)
    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
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
        str | None,
        typer.Option(
            "--color",
            help="Group into separate lines by this column",
            autocompletion=complete_column,
        ),
    ] = None,
    head: Annotated[
        int | None,
        typer.Option("--head", min=1, help="Only read the first N CSV rows"),
    ] = None,
    title: Annotated[
        str | None,
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
        typer.Option(
            "--where-not",
            help="Exclude rows: COL=value (case-insensitive)",
            autocompletion=complete_where,
        ),
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
        rprint(f"[red]Error:[/red] {_format_key_error(e)}")
        raise typer.Exit(1)
    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
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
        int | None,
        typer.Option("--head", min=1, help="Only read the first N CSV rows"),
    ] = None,
    sample: Annotated[
        int | None,
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
        typer.Option(
            "--where-not",
            help="Exclude rows: COL=value (case-insensitive)",
            autocompletion=complete_where,
        ),
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
        rprint(f"[red]Error:[/red] {_format_key_error(e)}")
        raise typer.Exit(1)
    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
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

        # Build data-quality table
        show_sentinels = any(s.null_sentinel_count > 0 for s in summaries)
        show_whitespace = any(s.whitespace_count > 0 for s in summaries)

        dq_table = Table(title=f"Data Quality: {file.name}")
        dq_table.add_column("Column", style="bold")
        dq_table.add_column("Nulls", justify="right")
        if show_sentinels:
            dq_table.add_column("Sentinels", justify="right")
        dq_table.add_column("Zeros", justify="right")
        dq_table.add_column("Mean", justify="right")
        dq_table.add_column("Stddev", justify="right")
        dq_table.add_column("Formats")
        if show_whitespace:
            dq_table.add_column("Whitespace", justify="right")
        dq_table.add_column("Mixed Types")
        dq_table.add_column("Mixed Examples")

        for s in summaries:
            cells = [
                s.name,
                str(s.null_count),
            ]
            if show_sentinels:
                cells.append(str(s.null_sentinel_count))
            cells.extend(
                [
                    str(s.zero_count) if s.mean is not None else "-",
                    f"{s.mean:.3f}" if s.mean is not None else "-",
                    f"{s.stddev:.3f}" if s.stddev is not None else "-",
                    "; ".join(f"{fmt}({count})" for fmt, count in s.date_formats) or "-",
                ]
            )
            if show_whitespace:
                cells.append(str(s.whitespace_count))
            cells.extend(
                [
                    s.mixed_type_pct or "-",
                    ", ".join(s.mixed_type_examples) or "-",
                ]
            )
            dq_table.add_row(*cells)

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

            renderables = [table, dq_table]
            if sample_table:
                renderables.append(sample_table)
            print(semantic_rich(*renderables), end="")
        else:
            rprint(table)
            rprint()
            rprint(dq_table)
            if sample_table:
                rprint()
                rprint(sample_table)


BLOCK_CHARS = ["░", "▒", "▓", "█"]


def _fill_block(pct: int) -> str:
    """Return a block character for a fill-rate percentage."""
    if pct <= 0:
        return " "
    elif pct <= 25:
        return BLOCK_CHARS[0]
    elif pct <= 50:
        return BLOCK_CHARS[1]
    elif pct <= 75:
        return BLOCK_CHARS[2]
    else:
        return BLOCK_CHARS[3]


def _render_grouped_bubble(
    gspec: GroupedBubbleSpec,
    chart_title: str,
    format_opt: str,
) -> None:
    """Render a GroupedBubbleSpec as a Rich table (visual or semantic)."""
    table = Table(title=chart_title)
    table.add_column("Group", style="bold")
    table.add_column("N", justify="right")
    for col_name in gspec.col_names:
        table.add_column(col_name, justify="center")

    for g_idx, label in enumerate(gspec.group_labels):
        cells = []
        for col_idx in range(len(gspec.col_names)):
            count = gspec.counts[g_idx][col_idx]
            if gspec.col_denoms:
                size = gspec.col_denoms[col_idx]
            else:
                size = gspec.group_sizes[g_idx]
            pct = round(count / size * 100) if size > 0 else 0
            block = _fill_block(pct)
            cells.append(f"{block} {pct}% ({count}/{size})")
        n_str = str(gspec.group_sizes[g_idx]) if gspec.group_sizes else ""
        table.add_row(label, n_str, *cells)

    # Overall footer
    if gspec.col_denoms:
        total_size = sum(gspec.col_denoms)
    else:
        total_size = sum(gspec.group_sizes)
    overall_cells = []
    for col_idx in range(len(gspec.col_names)):
        total_count = sum(
            gspec.counts[g][col_idx] for g in range(len(gspec.group_labels))
        )
        pct = round(total_count / total_size * 100) if total_size > 0 else 0
        block = _fill_block(pct)
        overall_cells.append(f"[dim]{block} {pct}% ({total_count}/{total_size})[/dim]")
    table.add_section()
    table.add_row("[bold]TOTAL[/bold]", str(total_size), *overall_cells)

    if format_opt == "semantic":
        from csvplot.semantic import semantic_rich

        print(semantic_rich(table), end="")
    else:
        rprint(table)


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
        str | None,
        typer.Option(
            "--color",
            help="Color rows by this column",
            autocompletion=complete_column,
        ),
    ] = None,
    top: Annotated[
        int | None,
        typer.Option("--top", min=1, help="Show only top N columns by fill-rate"),
    ] = None,
    head: Annotated[
        int | None,
        typer.Option("--head", min=1, help="Only read the first N CSV rows"),
    ] = None,
    sample: Annotated[
        int | None,
        typer.Option("--sample", min=1, help="Show N random rows in bubble output"),
    ] = None,
    title: Annotated[
        str | None,
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
        typer.Option(
            "--where-not",
            help="Exclude rows: COL=value (case-insensitive)",
            autocompletion=complete_where,
        ),
    ] = None,
    transpose: Annotated[
        bool,
        typer.Option("--transpose", help="Swap rows and columns"),
    ] = False,
    sort: Annotated[
        str | None,
        typer.Option("--sort", help="Sort rows: fill (most complete first), fill-asc, name"),
    ] = None,
    encode: Annotated[
        bool,
        typer.Option(
            "--encode",
            help="Auto-encode columns to col=value format",
        ),
    ] = False,
    group_by: Annotated[
        str | None,
        typer.Option(
            "--group-by",
            help="Aggregate by column: show fill-rate per group instead of per row",
            autocompletion=complete_column,
        ),
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

    chart_title = title if title else file.stem

    # --group-by + --sample is incompatible (aggregation needs all rows)
    if group_by and sample:
        rprint(
            "[red]Error:[/red] Cannot use --sample with --group-by"
            " (aggregation needs all rows)."
        )
        raise typer.Exit(1)

    # --group-by path: load grouped, then flow through sort/transpose
    if group_by:
        from csvplot.bubble import (
            load_bubble_grouped,
            sort_grouped_spec,
            transpose_grouped_spec,
        )

        try:
            gspec = load_bubble_grouped(
                path=file,
                cols=cols,
                y_col=y,
                group_by=group_by,
                max_rows=head,
                top=top,
                wheres=wheres or None,
                where_nots=where_nots or None,
                encode=encode,
            )
        except KeyError as e:
            rprint(f"[red]Error:[/red] {_format_key_error(e)}")
            raise typer.Exit(1)

        if sort:
            try:
                gspec = sort_grouped_spec(gspec, sort)
            except ValueError as e:
                rprint(f"[red]Error:[/red] {e}")
                raise typer.Exit(1)

        if transpose:
            gspec = transpose_grouped_spec(gspec)

        if not gspec.group_labels:
            rprint("[yellow]Warning:[/yellow] No data found.")
            raise typer.Exit(0)

        if format_opt == "compact":
            from csvplot.compact import compact_bubble_grouped

            print(compact_bubble_grouped(gspec, title=chart_title))
        else:
            _render_grouped_bubble(gspec, chart_title, format_opt)
        return

    try:
        spec = load_bubble_data(
            path=file,
            cols=cols,
            y_col=y,
            color_col=color,
            max_rows=head,
            sample_n=sample,
            top=top,
            wheres=wheres or None,
            where_nots=where_nots or None,
            encode=encode,
        )
    except KeyError as e:
        rprint(f"[red]Error:[/red] {_format_key_error(e)}")
        raise typer.Exit(1)
    except ValueError as e:
        rprint(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if sort:
        from csvplot.bubble import sort_bubble_spec

        try:
            spec = sort_bubble_spec(spec, sort)
        except ValueError as e:
            rprint(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    if transpose:
        from csvplot.bubble import transpose_bubble_spec

        spec = transpose_bubble_spec(spec)

    if not spec.y_labels:
        rprint("[yellow]Warning:[/yellow] No data found.")
        raise typer.Exit(0)

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
        symbol_palette = ["●", "■", "▲", "◆", "✦", "✚", "✖", "★", "⬟", "⬢", "◉", "◎"]
        max_label_width = 44

        def _truncate_label(value: str) -> str:
            if len(value) <= max_label_width:
                return value
            return value[: max_label_width - 1] + "…"

        color_map: dict[str, str] = {}
        symbol_map: dict[str, str] = {}
        legend_table: Table | None = None
        label_map_table: Table | None = None
        if color and spec.color_keys:
            unique_keys: list[str] = []
            seen_keys: set[str] = set()
            for key in spec.color_keys:
                if key not in seen_keys:
                    unique_keys.append(key)
                    seen_keys.add(key)
            color_map = {key: palette[i % len(palette)] for i, key in enumerate(unique_keys)}
            symbol_map = {
                key: symbol_palette[i % len(symbol_palette)] for i, key in enumerate(unique_keys)
            }
            legend_table = Table(title="Legend")
            legend_table.add_column("Cue", justify="center")
            legend_table.add_column(color)
            for key in unique_keys:
                style = color_map[key]
                symbol = symbol_map[key]
                legend_table.add_row(f"[{style}]{symbol}[/{style}]", key)

        # Build Rich table with Unicode dots
        table = Table(title=chart_title)
        table.add_column("Row", style="bold")
        for col_name in spec.col_names:
            table.add_column(col_name, justify="center")

        truncated_rows: list[tuple[int, str]] = []
        shown_labels: list[str] = []
        for row_idx, label in enumerate(spec.y_labels):
            row_num = row_idx + 1
            shown_label = _truncate_label(label)
            shown_labels.append(shown_label)
            if shown_label != label:
                truncated_rows.append((row_num, label))

        show_row_numbers = bool(truncated_rows)
        for row_idx, label in enumerate(spec.y_labels):
            row_num = row_idx + 1
            row_style = (
                color_map.get(spec.color_keys[row_idx], "")
                if color_map and row_idx < len(spec.color_keys)
                else ""
            )
            shown_label = shown_labels[row_idx]
            row_label = f"{row_num:>2}. {shown_label}" if show_row_numbers else shown_label
            label_cell = f"[{row_style}]{row_label}[/{row_style}]" if row_style else row_label
            cells = []
            row_symbol = (
                symbol_map.get(spec.color_keys[row_idx], "●")
                if symbol_map and row_idx < len(spec.color_keys)
                else "●"
            )
            for val in spec.matrix[row_idx]:
                if val:
                    dot_cell = (
                        f"[{row_style}]{row_symbol}[/{row_style}]"
                        if row_style
                        else f"[green]{row_symbol}[/green]"
                    )
                    cells.append(dot_cell)
                else:
                    cells.append("")
            table.add_row(label_cell, *cells)

        # Add TOTAL footer row with per-column fill-rates
        from csvplot.bubble import column_fill_rates

        rates = column_fill_rates(spec)
        total_cells = [f"[dim]{rates[col]}%[/dim]" for col in spec.col_names]
        table.add_section()
        table.add_row("[bold]TOTAL[/bold]", *total_cells)

        if truncated_rows:
            label_map_table = Table(title="Row Labels")
            label_map_table.add_column("#", justify="right")
            label_map_table.add_column("Full label")
            for row_num, full_label in truncated_rows:
                label_map_table.add_row(str(row_num), full_label)

        if spec.total_rows > len(spec.y_labels):
            table.caption = f"Showing {len(spec.y_labels)} of {spec.total_rows} rows"

        if format_opt == "semantic":
            from csvplot.semantic import semantic_rich

            extra_tables = [t for t in (legend_table, label_map_table) if t is not None]
            if extra_tables:
                print(semantic_rich(table, *extra_tables), end="")
            else:
                print(semantic_rich(table), end="")
        else:
            rprint(table)
            if legend_table:
                rprint()
                rprint(legend_table)
            if label_map_table:
                rprint()
                rprint(label_map_table)
