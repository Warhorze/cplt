# csvplot timeline - Tester Feedback

## Overall Impression

The tool looks nice and the terminal-based Gantt chart idea is great for quick data exploration without leaving the CLI. The color coding works well and the `--txt` labels help identify what each segment represents. The CLI interface with `--x` accepting multiple values for start/end pairs is clean.

## Main Issue: Multiple Lines Compacted Into One

The biggest usability problem is how rows with the same `--y` value get compacted onto a single horizontal line. When I run:

```
csvplot timeline --file data/timeplot2.csv \
  --x DH_PV_STARTDATUM --x DH_PV_EINDDATUM \
  --x EN_START_DATETIME --x EA_END_DATETIME \
  --y DH_FACING_NUMMER --color SH_ARTIKEL_S1 --txt SH_ARTIKEL_S1
```

All three data rows have `DH_FACING_NUMMER = 2006`, so they all land on the same y-position. The segments overlap and it becomes very hard to tell which segment belongs to which row. The layer offset (primary vs layer 1) is too subtle - the dots and half-blocks nearly merge into each other.

### What I expected

- Segments that overlap in time on the same y-label should be visually separated, either by stacking them or by adding enough vertical spacing between layers that you can clearly see each one.
- Or: some way to break ties on the y-axis (e.g. an option like `--y-detail` that sub-groups by another column within each y-label).

### What I got

- A single thick line where the primary and secondary layers are smashed together with ~0.15 vertical offset, which in practice looks like one line.
- Text labels overlap each other when segments are close in time range.

## Other Observations

1. **Text label overlap**: When multiple segments are close together, the `--txt` labels pile on top of each other and become unreadable. Some kind of collision avoidance or truncation would help.

2. **Legend clutter**: Each segment gets its own legend entry (e.g. "primary (120290146)", "layer 1 (120290146)"). With more data rows this would explode. A deduplicated legend by color_key would be cleaner.

3. **Small dataset looks fine, larger ones won't**: With only 3 rows and 1 unique y-value, the plot is already cramped. With real-world data (dozens of y-values, hundreds of segments), the compaction issue will be much worse.

4. **The layer concept is interesting but confusing**: Having `--x` accept pairs of start/end columns and rendering them as layers is powerful, but the visual distinction between layer 0 (half-block markers) and layer 1+ (dot markers) is too subtle in practice. Different line styles or clearer vertical separation would help.

5. **Open-end handling works well**: The `--open-end` flag correctly extends NULL end-dates to today, which is useful for ongoing records.

6. **Legend shows duplicates**: When using `--color SH_ARTIKEL_S1`, the legend shows "primary (120290146)" three separate times (once per segment). It should deduplicate and only show each color_key once.

7. **Using a different `--y` helps a lot**: When switching from `--y DH_FACING_NUMMER` (all rows = 2006) to `--y SH_ARTIKEL_S1` (unique per row), the chart immediately becomes readable with proper separation. This confirms the core problem isn't the rendering itself, but the lack of any sub-grouping when multiple rows share a y-value.

8. **Marker feature works nicely**: `--marker 2025-06-01 --marker-label "Release"` renders a clean red vertical line with label. Looks good.

9. **Error handling is solid**: Invalid column names give a clear error ("Column not found in CSV: 'NONEXISTENT'"), odd `--x` counts are caught, and the help text is well organized with the Formatting panel separation.

10. **Smart autocomplete ordering is clever but hard to verify**: The completions code sorts start-like columns first on even positions and end-like columns first on odd positions. Good idea, but the keyword sets (`start`, `begin`, `van`, `from` vs `end`, `eind`, `stop`, `tot`) might not cover all naming conventions. For this dataset, `DH_PV_STARTDATUM` matches "start" but `EA_END_DATETIME` doesn't match any end keyword since "end" is a substring of the longer token. Actually it does match since it checks `kw in col_lower` - so "end" in "ea_end_datetime" works. That's good.

11. **No way to filter or limit rows**: With larger CSVs, you'd want something like `--where "COLUMN=VALUE"` or `--head 50` to limit what gets plotted. Right now you'd have to pre-filter the CSV externally.

12. **Only one command so far (`timeline`)**: The top-level help shows just `timeline`. Would be good to see what other plot types are planned - scatter, bar, etc. The Typer subcommand structure is ready for it.
