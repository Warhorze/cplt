# Line Plot Design

## Goal

Show trends and changes over time/sequence with a stable, interpretable line shape.

## Should Generally Be In The Image

- Continuous, readable line trajectories for valid points
- Consistent x-axis ordering (chronological for date mode)
- Stable min/max annotation behavior in compact representation
- Explicit handling of missing/invalid x values

## Should Generally Not Be In The Image

- Crashes or empty output caused by sparse invalid dates
- Overly precise numeric labels that reduce readability
- Multiple series blending into an indistinguishable trace

## Review Scenarios

1. `line_trend`: baseline time-series rendering
2. `line_head`: reduced sample via `--head` to inspect scale and shape fidelity

## Acceptance Checklist

- Valid rows render in expected order
- Invalid/blank x values are handled without crash
- Compact min/max labels are human-readable (avoid excessive precision)
- Axis labels remain legible at default terminal width assumptions

## Feedback Trace

- 2026-02-14 (`feedback.md`): line no longer crashes on invalid x dates (regression fixed).
- 2026-02-14 (`feedback.md`): compact min/max precision currently verbose; keep as readability check.
