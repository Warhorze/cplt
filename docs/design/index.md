# Design Review Docs

This section formalises chart review for `csvplot`.

Each plot type has its own design doc with:

- what should generally be present in the rendered image
- what should generally be avoided
- review scenarios and acceptance checks
- known feedback history and regression watchouts

## Plot-Specific Docs

- [Timeline](timeline.md)
- [Bar](bar.md)
- [Line](line.md)
- [Bubble](bubble.md)

## Review Workflow

Generate fresh review artifacts:

```bash
bash scripts/generate_design_review_images.sh
```

This writes:

- PNG images to `assets/review/images/`
- raw command outputs to `assets/review/raw/`
- review summary report to `assets/review/REPORT.md`

Generated files are not meant to be hand-edited.

## Extra UX Pointers

Apply these additional checks across all plot types:

- Verify color encodings remain understandable without color alone (legend + alternate cue).
- Surface missing categorical values explicitly (for example `(missing)`).
- Prefer adaptive date tick precision based on visible range.
- Prevent label-heavy layouts from overwhelming the data region (use truncation/indexing patterns when needed).
- Include a compact interpretation summary when it materially improves scanability.
