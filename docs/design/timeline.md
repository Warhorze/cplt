# Timeline Plot Design

## Goal

Show interval-based data clearly across one or more date ranges, with readable grouping and unambiguous legend semantics.

## Should Generally Be In The Image

- Clear x-axis date progression and bounded plot area
- Readable y labels (composite labels allowed when multiple `--y` are used)
- Distinguishable segments for each range layer when multiple `--x` pairs are used
- Legend entries that map visual encodings to source columns/values when `--color` is used
- Marker visibility and label readability when `--marker` is present

## Should Generally Not Be In The Image

- Ambiguous legend labels where users cannot tell which layer or color mapping a segment belongs to
- Segments overflowing chart boundaries without clipping
- Silent omission of rows without any warning when date parsing fails
- Marker labels that overlap data so heavily they become unreadable

## Review Scenarios

1. `timeline_legend`: multi-layer + color + marker; validate legend clarity
2. `timeline_zoom`: filtered window via `--from`/`--to`; validate temporal zoom behavior

## Acceptance Checklist

- Legend uses explicit layer naming and mapped value context
- Marker line and label are visible and not detached from marker date
- Multi-layer glyphs remain visually separable
- Date axis remains monotonic and readable
- If rows are skipped due to invalid dates, the run surfaces a warning

## Feedback Trace

- 2026-02-16: Prior feedback highlighted unclear legend interpretation in timeline outputs. Keep legend clarity as a blocking review point.
- 2026-02-14 (`feedback.md`): invalid non-empty end dates can result in silent row drops under open-end handling. Track as data-loss UX risk.
