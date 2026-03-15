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

## `cplt`

```bash
cplt [OPTIONS] COMMAND [ARGS]...
```

Plot data from CSV files directly in the terminal.

### Global Options

| Option | Type | Required | Repeatable | Default | Description |
| --- | --- | --- | --- | --- | --- |
| --install-completion | BOOLEAN | No | No |  | Install completion for the current shell. |
| --show-completion | BOOLEAN | No | No |  | Show completion for the current shell, to copy it or customize the installation. |

## `cplt timeline`

```bash
cplt timeline [OPTIONS]
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
| --vline | TEXT | No | No |  | Vertical reference line date (YYYY-MM-DD) |
| --label | TEXT | No | No |  | Label for the vertical reference line |
| --dot | TEXT | No | Yes |  | Date column(s) to render as per-row dot markers |
| --open-end / --no-open-end | BOOLEAN | No | No | True | Replace NULL/sentinel end dates with today |
| --y-detail | TEXT | No | No |  | Sub-group within --y by appending this column's value |
| --head | INTEGER RANGE | No | No |  | Only read the first N CSV rows |
| --from | TEXT | No | No |  | Zoom start date (YYYY-MM-DD), only show data from this date |
| --to | TEXT | No | No |  | Zoom end date (YYYY-MM-DD), only show data up to this date |
| --title | TEXT | No | No |  | Chart title (defaults to filename) |
| --where | TEXT | No | Yes |  | Filter rows: COL=value (case-insensitive, repeat for OR/AND) |
| --where-not | TEXT | No | Yes |  | Exclude rows: COL=value (case-insensitive) |
| --export | TEXT | No | No |  | Export chart to PNG file |
| --format | TEXT | No | No | visual | Output format: visual, semantic, or compact |

## `cplt bar`

```bash
cplt bar [OPTIONS]
```

Plot a bar chart of value counts from a CSV column.

### Options

| Option | Type | Required | Repeatable | Default | Description |
| --- | --- | --- | --- | --- | --- |
| --file, -f | FILE | Yes | No |  | Path to CSV file |
| --column, -c | TEXT | Yes | No |  | Column to count values of |
| --sort | TEXT | No | No | value | Sort by: value (desc count), label (alpha), none (CSV order) |
| --horizontal | BOOLEAN | No | No | False | Use horizontal bars (visual format only) |
| --labels | BOOLEAN | No | No | False | Show exact values on bars (visual format only) |
| --top | INTEGER RANGE | No | No |  | Show only the top N categories |
| --head | INTEGER RANGE | No | No |  | Only read the first N CSV rows |
| --title | TEXT | No | No |  | Chart title (defaults to filename) |
| --where | TEXT | No | Yes |  | Filter rows: COL=value (case-insensitive) |
| --where-not | TEXT | No | Yes |  | Exclude rows: COL=value (case-insensitive) |
| --export | TEXT | No | No |  | Export chart to PNG file |
| --format | TEXT | No | No | visual | Output format: visual, semantic, or compact |

## `cplt line`

```bash
cplt line [OPTIONS]
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
| --export | TEXT | No | No |  | Export chart to PNG file |
| --format | TEXT | No | No | visual | Output format: visual, semantic, or compact |

## `cplt summarise`

```bash
cplt summarise [OPTIONS]
```

Print a summary of a CSV file — column types, counts, nulls, and smart distribution views.

### Options

| Option | Type | Required | Repeatable | Default | Description |
| --- | --- | --- | --- | --- | --- |
| --file, -f | FILE | Yes | No |  | Path to CSV file |
| --head | INTEGER RANGE | No | No |  | Only read the first N CSV rows |
| --sample | INTEGER RANGE | No | No |  | Show N random sample rows as preview |
| --where | TEXT | No | Yes |  | Filter rows: COL=value (case-insensitive) |
| --where-not | TEXT | No | Yes |  | Exclude rows: COL=value (case-insensitive) |
| --export | TEXT | No | No |  | Export chart to PNG file |
| --category | INTEGER RANGE | No | No | 10 | Category threshold: columns with <= N unique values are treated as categorical |
| --format | TEXT | No | No | visual | Output format: visual, semantic, or compact |

### Summary table

The main table shows one row per CSV column:

| Column | Meaning |
| --- | --- |
| Type | Detected type: `numeric`, `date`, or `text` |
| Nulls | Number of empty/missing rows |
| Unique | Number of distinct non-null values |
| Min / Max | Range for numeric and date columns, `-` for text |
| Distribution | Smart view based on column classification (see below) |

### How Distribution works

Columns are auto-classified based on `--category N` (default 10):

- **Categorical** (`unique_count <= N`): shows the top 10 values with percentages, e.g. `male 65%, female 35%`. If there are more values beyond the top 10, they are lumped into `other`. This applies regardless of detected type — a numeric column like `Survived` with only 2 values (`0`, `1`) is shown as categorical.
- **ID-like** (`unique_count == row_count` and `unique_count > N`): shows `all unique`. These are columns like `PassengerId` or `Name` where every value is different — frequency lists would be useless.
- **Numeric** (non-categorical): shows a sparkline histogram with min/max range, e.g. `▃▂▄█▇▆▄▃▂▂▁▁ 0.42 .. 80.0`. The 12-bin histogram shows the shape of the distribution at a glance.
- **Other** (text with many unique values): shows top 10 values with raw counts, e.g. `G6(4), C23 C25 C27(4)`.

Use `--category 5` for stricter classification (fewer categoricals) or `--category 20` for looser (more categoricals).

### Data Quality table

The second table shows data quality diagnostics:

| Column | Meaning |
| --- | --- |
| Nulls | Number of empty/missing rows |
| Sentinels | Values matching common null patterns: `NA`, `N/A`, `null`, `None`, etc. (hidden if all zero) |
| Zeros | Count of values that parse to `0.0` — `-` if the column has no numeric values |
| Mean / Stddev | Population mean and standard deviation — `-` if the column has no numeric values |
| Formats | Date format patterns detected with counts, e.g. `YYYY-MM-DD(14); DD/MM/YYYY(2)` — `-` if no dates |
| Whitespace | Values with leading/trailing whitespace (hidden if all zero) |

The `-` vs `0` distinction: `-` means the metric does not apply to this column (e.g. Zeros for a pure text column), while `0` means the metric applies but the count is zero (e.g. Zeros for a numeric column with no zero values).

## `cplt bubble`

```bash
cplt bubble [OPTIONS]
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
| --sample | INTEGER RANGE | No | No |  | Show N random rows in bubble output |
| --title | TEXT | No | No |  | Chart title (defaults to filename) |
| --where | TEXT | No | Yes |  | Filter rows: COL=value (case-insensitive) |
| --where-not | TEXT | No | Yes |  | Exclude rows: COL=value (case-insensitive) |
| --transpose | BOOLEAN | No | No | False | Swap rows and columns |
| --sort | TEXT | No | No |  | Sort rows: fill (most complete first), fill-asc, name |
| --encode | BOOLEAN | No | No | False | Auto-encode columns to col=value format |
| --group-by | TEXT | No | No |  | Aggregate by column: show fill-rate per group instead of per row |
| --export | TEXT | No | No |  | Export chart to PNG file |
| --format | TEXT | No | No | visual | Output format: visual, semantic, or compact |
