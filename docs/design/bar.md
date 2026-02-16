# Bar Plot Design

## Goal

Provide quick categorical distribution insight with obvious ordering and proportion cues.

## Should Generally Be In The Image

- Category labels that are readable and aligned with bars
- Count scale that makes relative magnitude obvious
- Deterministic ordering behavior matching `--sort`
- Clear truncation behavior when `--top` is used

## Should Generally Not Be In The Image

- Label clipping that makes categories indistinguishable
- Ordering that does not match selected sort mode
- Visual clutter from too many categories without truncation controls
- Misleading output differences when format-specific flags are ignored silently

## Review Scenarios

1. `bar_distribution`: baseline distribution for a known categorical column
2. `bar_sort_top`: validate sorting and `--top` reduction behavior

## Acceptance Checklist

- Counts are consistent with source CSV for the selected subset
- Sort mode (`value`, `label`, `none`) is reflected correctly
- Top-N output includes only the expected categories
- Axis scale supports quick magnitude comparison

## Feedback Trace

- 2026-02-14 (`feedback.md`): `--horizontal` has no effect in compact mode (likely by design). Keep this documented to avoid reviewer confusion.
