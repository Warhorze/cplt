# Changelog

## 0.1.0 — Initial Release

### Commands

- **timeline** — Gantt-style date-range charts with layered start/end pairs, `--y-detail` sub-grouping, `--vline`/`--label` reference lines, and `--dot` per-row date markers
- **bar** — Value-count bar charts with `--sort`, `--top`, `--horizontal`, `--labels`, and per-category palette colours
- **line** — Numeric and date-indexed line charts with `--from`/`--to` date filtering
- **bubble** — Presence/absence dot matrix with `--sort`, `--transpose`, `--group-by` aggregation, `--encode` auto-encoding, `--sample`, `--top`, `--color` row styling, and fill-rate summary footer
- **summarise** — CSV profiling: column types, null counts, top values with frequencies, plus data-quality stats (null sentinels, zeros, mean/stddev, date formats, whitespace issues)

### Output formats

- **visual** — Full-colour terminal charts via plotext (timeline, bar, line) and Rich tables (bubble, summarise)
- **compact** — Token-efficient ASCII renderers with RLE encoding, designed for LLM consumption
- **semantic** — ANSI-stripped plain-text capture for accessibility and diffing

### Export

- `--export <path>.png` on all five commands — renders ANSI terminal output to PNG with braille dot rendering and supersampled anti-aliasing

### Filtering

- `--where COL=value` and `--where-not COL=value` on all commands with case-insensitive matching
- `--head N` to limit input rows

### Shell integration

- Context-aware tab completion for `--where` values (column names, then `COL=value` pairs)
- Completion for CSV file paths with tilde expansion

### Developer tooling

- CLI smoke test script (`scripts/run_cli_smoke.sh`)
- Design review image generator (`scripts/generate_design_review_images.sh`)
- Animated demo GIF recorder via VHS (`scripts/generate_demos.sh`)
- CLI docs generator (`scripts/generate_cli_docs.sh`)
- MkDocs documentation site
- UX test suite with combination matrix coverage
- "Ready for Release" checklist in DEVELOPERS.md
