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

- SVG images to `assets/review/images/`
- raw command outputs to `assets/review/raw/`
- review summary report to `assets/review/REPORT.md`

Generated files are not meant to be hand-edited.
