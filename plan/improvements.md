# csvplot Improvement Plan — Based on Tester Feedback

## Context

After initial implementation, a tester exercised csvplot with `data/timeplot2.csv` (3 rows sharing `DH_FACING_NUMMER=2006`). The core problem: segments with the same `--y` value pile on one line and become unreadable. Secondary issues include duplicate legend entries, text label overlap, and subtle layer distinction. This plan addresses all 6 actionable items from `feedback.md`.

---

## Changes Overview

| # | Issue | Priority | Files |
|---|-------|----------|-------|
| 1 | Segments with same y-value overlap | Critical | `renderer.py`, `cli.py`, `models.py` |
| 2 | Legend shows duplicates | High | `renderer.py` |
| 3 | Text labels overlap | High | `renderer.py` |
| 4 | Layer visual distinction too subtle | Medium | `renderer.py` |
| 5 | No row filtering (`--where`, `--head`) | Low | `cli.py`, `reader.py` |
| 6 | `--txt` option in README | Low | `readme.md` |

---

## 1. Stacking segments within the same y-label (Critical)

**Problem**: All segments sharing a `y_label` land on the same y-position. The 0.15-unit layer offset is invisible in practice.

**Approach — sub-row stacking**:

In `renderer.py`, after collecting segments, compute a **sub-row index** per segment within each y-label. Segments that overlap in time get different sub-rows; non-overlapping segments can share a sub-row (greedy interval scheduling).

```
y_label "2006":
  sub-row 0: |---seg A---|
  sub-row 1:        |---seg B---|
  sub-row 2:                        |---seg C---|  ← could share row 0 (no overlap)
```

Implementation:

- Add helper `_assign_sub_rows(segments) -> dict[id(seg), int]` in `renderer.py`
  - Group segments by `(y_label, layer)`
  - Sort by start time
  - Greedy pack: for each segment, find the first sub-row where it doesn't overlap existing segments, assign it there
- Change y-position calculation:
  - Current: `y = y_index[label] ± layer * 0.15`
  - New: `y = base + sub_row * SUB_ROW_HEIGHT + layer_offset`
  - `SUB_ROW_HEIGHT = 0.35` (enough visual gap within a y-group)
- Update `plot_height` calculation to account for max sub-rows per y-label
- Update `yticks` to point at the center of each y-label group

Additionally, add a **`--y-detail <col>`** CLI option that appends a secondary column to create composite y-labels (e.g., `"2006 | 120290146"`), giving users explicit control over sub-grouping.

**Files to modify**:

- `renderer.py` (lines 62-76, 82-114): sub-row assignment + new y-position math
- `cli.py`: add `--y-detail` option, combine with `--y` before passing to `load_segments`
- `models.py`: no changes needed (y_label is already a string, composite labels work)

**User Suggestion**:
Try to ensure each row is an individual line in the graph this should be the default behavior, later we'll probably add options to add aggregations (similar to sql sum, min/max enc. to tell csvplot how to handle multiple instances)

---

## 2. Deduplicate legend entries (High)

**Problem**: Each `plt.plot()` call creates a legend entry. With 3 segments of the same color_key, the legend shows "primary (120290146)" three times.

**Approach**: Track which `(layer_name, color_key)` combos have already been added to the legend. For subsequent duplicates, pass `label=None` (or `label="_nolegend_"` if plotext requires a string) to suppress the legend entry.

```python
legend_seen: set[str] = set()

for seg in spec.segments:
    legend_key = f"{layer_name}|{seg.color_key}"
    label = formatted_label if legend_key not in legend_seen else "_nolegend_"
    legend_seen.add(legend_key)
    plt.plot(..., label=label)
```

**Files to modify**:

- `renderer.py` (lines 82-114): add `legend_seen` set, conditionally set label

**User Suggestion**:
Folow the same color schema as Raintbow CSV it creates this high contrast difference between columns which makes it nice to look at, reuse colors in the same way as rainbow csv does, if we have more than 16 colors we need to come up with a strategy that we don't reuse colors without the user knowing maybe auto set --txt? with warning ofcourse. Also we could render the legend seperately so we don't overwrite precious space. All things considered I don't think it is usefull to use a lengend when we have more than 16 colors we need to come up with something else.

---

## 3. Text label collision avoidance (High)

**Problem**: When segments are close in time, their `--txt` labels overlap at midpoints.

**Approach — vertical stagger + truncation**:

1. After collecting all `text_labels`, sort by x-position
2. For labels that are "too close" horizontally (within ~5% of the x-axis range), alternate their y-offset: `+0.20` / `+0.35`
3. Truncate long labels to a max character count (e.g., 15 chars + "…")
4. Skip rendering a label entirely if it would overlap a previously placed label at the same y-position (simple greedy filter)

**Files to modify**:

- `renderer.py` (lines 78, 95-97, 112-118): label collection and rendering logic

**User Suggestion**:

---

## 4. Improve layer visual distinction (Medium)

**Problem**: `"dot"` vs `"hd"` markers with 0.15 offset look like one thick line.

**Approach**:

- Increase layer offset to work with the new sub-row stacking (handled by change #1)
- Use more distinct marker styles:
  - Layer 0 (primary): `"hd"` (half-diamond) — keep as is
  - Layer 1: `"braille"` or `"fhd"` (filled half-diamond) for stronger visual
  - Layer 2+: `"dot"` — keep for tertiary
- Add a dashed-style effect for non-primary layers by plotting with lower opacity if plotext supports it, otherwise rely on the increased spacing from sub-row stacking

**Files to modify**:

- `renderer.py` (lines 88-93): marker selection per layer

---

## 5. Add `--head` row filtering (Low)

**Problem**: No way to limit rows from large CSVs without external preprocessing.

**Approach**: Add `--head N` option to `cli.py` that passes through to `load_segments()`, which stops yielding segments after N CSV rows.

A full `--where` filter is more complex (expression parsing, type coercion) and can be deferred. `--head N` covers the most common use case with minimal code.

**Files to modify**:

- `cli.py`: add `--head` Typer option (Optional[int], default None)
- `reader.py` (`load_segments`, line ~30): add `max_rows` parameter, break after N rows

---

## 6. Document `--txt` in README (Low)

The `--txt` option exists in the CLI but is missing from the CLI reference table in `readme.md`.

**Files to modify**:

- `readme.md`: add `--txt <col>` row to the argument table

---

## Implementation Order

1. **Legend dedup** (#2) — smallest change, immediate visual improvement
2. **Sub-row stacking** (#1) — the critical fix, most code changes
3. **Layer distinction** (#4) — pairs with #1 since both touch segment rendering
4. **Text label collision** (#3) — depends on new y-positions from #1
5. **`--head` filtering** (#5) — independent, quick addition
6. **README update** (#6) — trivial

---

## Verification

1. **Regression**: `pytest` passes (existing tests untouched)
2. **Overlap fix**: `csvplot timeline -f data/timeplot2.csv --x DH_PV_STARTDATUM --x DH_PV_EINDDATUM --x EN_START_DATETIME --x EA_END_DATETIME --y DH_FACING_NUMMER --color SH_ARTIKEL_S1 --txt SH_ARTIKEL_S1` — segments visually separated on distinct sub-rows
3. **Legend**: same command — each color_key appears once per layer in legend
4. **Text labels**: same command — labels don't overlap
5. **`--y-detail`**: `--y DH_FACING_NUMMER --y-detail SH_ARTIKEL_S1` — creates composite y-labels
6. **`--head`**: `csvplot timeline -f data/timeplot.csv --x ... --y ... --head 3` — only first 3 rows plotted
7. **Different y-column still works**: `--y SH_ARTIKEL_S1` (unique values) — renders as before, no sub-row stacking needed
