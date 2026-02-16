# Bubble Plot Design

## Goal

Communicate presence/absence patterns across selected columns with row-level readability.

## Should Generally Be In The Image

- Clear matrix grid with unambiguous present/absent markers
- Legible row labels and selected column headers
- Stable column ordering after optional `--top` filtering
- Distinguishable row styling when `--color` is applied

## Should Generally Not Be In The Image

- Marker ambiguity where absence and presence symbols are easy to confuse
- Row labels so long they fully dominate matrix readability
- `--color` accepted but producing no visible effect
- Hidden filtering/truncation behavior that is not obvious to reviewer

## Review Scenarios

1. `bubble_matrix`: baseline matrix correctness for known columns
2. `bubble_top`: verify top-N column reduction behavior
3. `bubble_color_effect`: compare visual outputs with and without `--color`

## Acceptance Checklist

- Presence markers match CSV null/non-null values for sampled rows
- Headers and row labels remain readable at default width
- `--top` returns the expected subset of columns
- `--color` visibly changes visual output (or is explicitly documented as unsupported)

## Feedback Trace

- 2026-02-16: Prior feedback called out uncertainty around bubble `--color` effect; keep this as a mandatory regression check.
- 2026-02-14 (`feedback.md`): `bubble --color` is accepted and expected to color rows in visual mode.
