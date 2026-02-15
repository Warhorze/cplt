# CLI Reference

This page is auto-generated from CLI command metadata.

Regenerate with:

```bash
bash scripts/generate_cli_docs.sh
```

## Commands

| Command | Description |
| --- | --- |
| `timeline` | Plot timeline/Gantt-style ranges from a CSV file. |
| `bar` | Plot a bar chart of value counts from a CSV column. |
| `line` | Plot a line chart from CSV columns. |
| `summarise` | Print a summary of a CSV file — column types, counts, nulls, top values. |
| `bubble` | Plot a presence/absence dot matrix from CSV columns. |

## `csvplot`

```bash
csvplot [OPTIONS] COMMAND [ARGS]...
```

Plot data from CSV files directly in the terminal.

### Global Options

| Option | Type | Required | Repeatable | Default | Description |
| --- | --- | --- | --- | --- | --- |
| --install-completion | BOOLEAN | No | No |  | Install completion for the current shell. |
| --show-completion | BOOLEAN | No | No |  | Show completion for the current shell, to copy it or customize the installation. |

## `csvplot timeline`

```bash
csvplot timeline [OPTIONS]
```

Plot timeline/Gantt-style ranges from a CSV file.

### Options

| Option | Type | Required | Repeatable | Default | Description |
| --- | --- | --- | --- | --- | --- |
| --file, -f | FILE | Yes | No |  | Path to CSV file |
| --x | TEXT | Yes | Yes |  | Time-range columns as start/end pairs. Example: --x START --x END for one layer, --x S1 --x E1 --x S2 --x E2 for two layers |
| --y | TEXT | Yes | Yes |  | Categorical Y-axis column(s); repeat to combine |
| --color | TEXT | No | No |  | Color rows by this column |
| --txt | TEXT | No | No |  | Label segments with this column's value (visual format only) |
| --marker | TEXT | No | No |  | Vertical marker date (YYYY-MM-DD) |
| --marker-label | TEXT | No | No |  | Label for the marker line |
| --open-end / --no-open-end | BOOLEAN | No | No | True | Replace NULL/sentinel end dates with today |
| --y-detail | TEXT | No | No |  | Sub-group within --y by appending this column's value |
| --head | INTEGER RANGE | No | No |  | Only read the first N CSV rows |
| --from | TEXT | No | No |  | Zoom start date (YYYY-MM-DD), only show data from this date |
| --to | TEXT | No | No |  | Zoom end date (YYYY-MM-DD), only show data up to this date |
| --title | TEXT | No | No |  | Chart title (defaults to filename) |
| --where | TEXT | No | Yes |  | Filter rows: COL=value (case-insensitive, repeat for OR/AND) |
| --where-not | TEXT | No | Yes |  | Exclude rows: COL=value (case-insensitive) |
| --format | TEXT | No | No | visual | Output format: visual, semantic, or compact |

## `csvplot bar`

```bash
csvplot bar [OPTIONS]
```

Plot a bar chart of value counts from a CSV column.

### Options

| Option | Type | Required | Repeatable | Default | Description |
| --- | --- | --- | --- | --- | --- |
| --file, -f | FILE | Yes | No |  | Path to CSV file |
| --column, -c | TEXT | Yes | No |  | Column to count values of |
| --sort | TEXT | No | No | value | Sort by: value (desc count), label (alpha), none (CSV order) |
| --horizontal | BOOLEAN | No | No | False | Use horizontal bars (visual format only) |
| --top | INTEGER RANGE | No | No |  | Show only the top N categories |
| --head | INTEGER RANGE | No | No |  | Only read the first N CSV rows |
| --title | TEXT | No | No |  | Chart title (defaults to filename) |
| --where | TEXT | No | Yes |  | Filter rows: COL=value (case-insensitive) |
| --where-not | TEXT | No | Yes |  | Exclude rows: COL=value (case-insensitive) |
| --format | TEXT | No | No | visual | Output format: visual, semantic, or compact |

## `csvplot line`

```bash
csvplot line [OPTIONS]
```

Plot a line chart from CSV columns.

### Options

| Option | Type | Required | Repeatable | Default | Description |
| --- | --- | --- | --- | --- | --- |
| --file, -f | FILE | Yes | No |  | Path to CSV file |
| --x | TEXT | Yes | No |  | X-axis column (date or sequential) |
| --y | TEXT | Yes | Yes |  | Y-axis column(s) (numeric); repeat for multiple lines |
| --color | TEXT | No | No |  | Group into separate lines by this column |
| --head | INTEGER RANGE | No | No |  | Only read the first N CSV rows |
| --title | TEXT | No | No |  | Chart title (defaults to filename) |
| --where | TEXT | No | Yes |  | Filter rows: COL=value (case-insensitive) |
| --where-not | TEXT | No | Yes |  | Exclude rows: COL=value (case-insensitive) |
| --format | TEXT | No | No | visual | Output format: visual, semantic, or compact |

## `csvplot summarise`

```bash
csvplot summarise [OPTIONS]
```

Print a summary of a CSV file — column types, counts, nulls, top values.

### Options

| Option | Type | Required | Repeatable | Default | Description |
| --- | --- | --- | --- | --- | --- |
| --file, -f | FILE | Yes | No |  | Path to CSV file |
| --head | INTEGER RANGE | No | No |  | Only read the first N CSV rows |
| --sample | INTEGER RANGE | No | No |  | Show N random sample rows as preview |
| --where | TEXT | No | Yes |  | Filter rows: COL=value (case-insensitive) |
| --where-not | TEXT | No | Yes |  | Exclude rows: COL=value (case-insensitive) |
| --format | TEXT | No | No | visual | Output format: visual, semantic, or compact |

## `csvplot bubble`

```bash
csvplot bubble [OPTIONS]
```

Plot a presence/absence dot matrix from CSV columns.

### Options

| Option | Type | Required | Repeatable | Default | Description |
| --- | --- | --- | --- | --- | --- |
| --file, -f | FILE | Yes | No |  | Path to CSV file |
| --cols | TEXT | Yes | Yes |  | Columns to check for presence/absence |
| --y | TEXT | Yes | No |  | Row label column |
| --color | TEXT | No | No |  | Color rows by this column |
| --top | INTEGER RANGE | No | No |  | Show only top N columns by fill-rate |
| --head | INTEGER RANGE | No | No |  | Only read the first N CSV rows |
| --title | TEXT | No | No |  | Chart title (defaults to filename) |
| --where | TEXT | No | Yes |  | Filter rows: COL=value (case-insensitive) |
| --where-not | TEXT | No | Yes |  | Exclude rows: COL=value (case-insensitive) |
| --format | TEXT | No | No | visual | Output format: visual, semantic, or compact |
