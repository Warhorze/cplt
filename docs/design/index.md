# Design Review Docs

> Cross-cutting UX checklist and review workflow: [`DEVELOPERS.md`](../../DEVELOPERS.md#ux-review)

Each plot type has its own design doc with acceptance criteria, review scenarios, and feedback history:

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
