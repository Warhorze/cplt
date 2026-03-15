# Histogram Design

## Goal

Visualise the distribution of a numeric column with configurable binning and summary statistics.

## Should Generally Be In The Image

- Bin-range labels on x-axis covering the full value range
- Bar heights reflecting relative frequency per bin
- Stats overlay: n, null count, mean, median, stddev
- Title reflecting the file or user-specified title

## Should Generally Not Be In The Image

- Overlapping or unreadable bin labels
- Missing edge bins that hide outliers
- Stats that don't match the actual data subset (e.g. after --where filtering)

## Review Scenarios

1. `hist_basic`: baseline histogram for a known numeric column
2. `hist_bins`: validate custom `--bins` count overrides auto binning
3. `hist_filtered`: validate stats correctness after `--where` filtering

## Acceptance Checklist

- Bin count matches `--bins` when specified, or auto-selected via sqrt(n) clamped [5,30]
- Sum of bin counts equals total non-null values
- Stats (mean, median, stddev) are consistent with source data
- Single-value edge case produces a single bin without crash
- Compact format shows sparkline with correct range labels

## Feedback Trace

(none yet)
