# Architecture

> Canonical reference: [`DEVELOPERS.md`](../DEVELOPERS.md#architecture)

This file is kept for the MkDocs site. See DEVELOPERS.md for the full architecture overview, module layout, and behavior contracts.

## Quick Summary

Data flows linearly: **CLI args → reader → PlotSpec → renderer → terminal**

```text
src/cplt/
  cli.py          # Typer command definitions + arg validation
  reader.py       # timeline/bar/line CSV loaders + datetime parsing + row filters
  bubble.py       # bubble matrix loader + falsy detection
  summarise.py    # CSV summary/profiling logic
  models.py       # Segment/VLine/PlotSpec/BarSpec/LineSpec/HistSpec dataclasses
  renderer.py     # plotext visual rendering (timeline/bar/line/hist)
  compact.py      # compact token-efficient rendering
  semantic.py     # ANSI-stripped rendering helpers
  completions.py  # column/date/value shell completion
```
