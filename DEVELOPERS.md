# Developer Guide

This file contains contributor workflows that are intentionally kept out of the user-facing `README.md`.

## UX Review Flow

Use this loop when reviewing chart quality and regressions:

1. Generate or update showcase images:

```bash
bash scripts/generate_readme_images.sh
```

2. Generate design review artifacts and report:

```bash
bash scripts/generate_design_review_images.sh
```

3. Review plot-specific criteria in:

- `docs/design/timeline.md`
- `docs/design/bar.md`
- `docs/design/line.md`
- `docs/design/bubble.md`

4. Check generated review report:

- `assets/review/REPORT.md`

5. For color behavior (for example bubble `--color`), use the generated PNGs plus the visual output checks in `assets/review/raw/`.

## Extra UX Pointers

Use these as cross-cutting checks during any chart review:

- Ensure `--color` has a non-color fallback cue (symbol/style) so output remains interpretable in low-color terminals and static screenshots.
- Normalize missing categorical values to explicit labels like `(missing)` instead of unlabeled buckets.
- Keep date tick formatting adaptive to time span to reduce axis noise.
- Prefer compact row-label handling (truncate + reference table) when labels dominate matrix readability.
- Add a short interpretation footer where possible (for example top category and missing count) to reduce scan effort.

## Automated UX Tests

The `tests/ux/` suite covers functional CLI behavior end-to-end (complementing the manual visual review above):

- **Format matrix** — 5 commands x 3 formats = 15 parameterized cases (`test_format_matrix.py`)
- **Option behavior** — per-command checks for every optional flag (`test_options_ux.py`)
- **Error message quality** — guards that errors are actionable, not tracebacks (`test_error_ux.py`)
- **Scale** — 500–10K row stress tests (`test_scale_ux.py`)

```bash
uv run pytest tests/ux/
```

See `plan/ux-testing.md` for the full coverage matrix and test design.

## Docs Tooling

- CLI reference: `docs/cli.md`
- MkDocs site source: `docs/` and `mkdocs.yml`
- Design review docs: `docs/design/`

Regenerate CLI docs:

```bash
bash scripts/generate_cli_docs.sh
```

Regenerate README images:

```bash
bash scripts/generate_readme_images.sh
```

Generate design review artifacts (plot-specific review images + report):

```bash
bash scripts/generate_design_review_images.sh
```

Preview docs locally:

```bash
uv sync --extra docs
uv run mkdocs serve
```

## Development Checks

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src/ tests/
uv run pyright
```
