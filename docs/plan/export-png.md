# Plan: Add `--export <path>` PNG export to csvplot

## Context

csvplot renders charts to the terminal using ANSI escape codes (plotext for timeline/bar/line, Rich for bubble/summarise). Users want to save these as PNG images for sharing in docs, Slack, etc. Pillow is already a dependency. Earlier research evaluated Rich SVG (broken braille/box glyphs, cairo crashes), ansitoimg (same issues + playwright dep), and Pillow direct rendering (works for all chart types). Pillow won.

## Scope

- `--export <path.png>` option on all 5 commands (timeline, bar, line, bubble, summarise)
- Only works with `--format visual` (default) — errors if combined with compact/semantic
- Pillow-based ANSI → PNG renderer (no native OS screenshot)
- Line charts use braille ANSI capture (same as all other charts)

## Architecture

```
CLI --export path.png
  → force build=True to capture ANSI canvas string
  → pass canvas to export_png(ansi_text, path)
  → export.py parses ANSI, renders char-by-char into Pillow Image
  → saves PNG
```

For plotext charts (timeline, bar, line): use `render*(spec, build=True)` to get ANSI string.
For Rich charts (bubble, summarise): use `Console(record=True)` to capture ANSI string.

## Implementation Steps

### Step 1: Add ANSI → PNG renderer (`src/csvplot/export.py`)

New module with a single public function:

```python
def export_png(ansi_text: str, out_path: str, font_size: int = 16) -> None
```

Internals:
- **ANSI parser**: handle SGR codes — basic colors (30-37, 90-97), 256-color (`38;5;N`), truecolor (`38;2;R;G;B`), reset, bold→bright mapping
- **Cell-grid renderer**: fixed-width cells based on `font.getlength("M")`, center each glyph in its cell
- **Braille renderer**: detect U+2800–U+28FF, decode bit pattern, draw circles (r=0.25×cell_w, mx=0.10, my=0.04)
- **2× supersampling**: render at double size, downscale with LANCZOS
- **Font fallback chain**: DejaVu Sans Mono → Liberation Mono → Consolas → Courier New → default
- **Theme**: bg `#1E1E1E`, fg `#CCCCCC`, 16px base font, 16px padding

TDD tests in `tests/test_export.py`:
1. `test_export_png_creates_file` — basic ANSI string → PNG file exists
2. `test_export_png_dimensions` — image dimensions match expected grid (cols × rows)
3. `test_ansi_parser_basic_colors` — parser extracts fg/bg from SGR codes
4. `test_ansi_parser_256_color` — parser handles `38;5;N`
5. `test_braille_rendering` — braille chars produce non-background pixels in expected dot positions

### Step 2: Wire `--export` into CLI (`src/csvplot/cli.py`)

Add `--export` option to all 5 commands. Pattern:

```python
export: Annotated[Optional[str], typer.Option(help="Export to PNG file")] = None,
```

At the format-selection point in each command:
- If `export` is set and `format_opt != "visual"`: error and exit
- If `export` is set: force `build=True`, capture ANSI canvas, call `export_png(canvas, export)`
- Still show visual output to terminal as well (user sees the chart AND gets the file)

**For plotext commands** (timeline, bar, line):
```python
if export:
    canvas = _require_canvas(render_bar(spec, build=True))
    export_png(canvas, export)
    render_bar(spec)  # also show in terminal
```

**For Rich commands** (bubble, summarise):
Need to capture Rich table output as ANSI string. Add helper:
```python
def _capture_rich_ansi(*renderables) -> str:
    console = Console(record=True, width=120)
    for r in renderables:
        console.print(r)
    return console.export_text(styles=True)
```

TDD tests in `tests/test_export_integration.py`:
1. `test_export_creates_png_file` — run CLI with `--export /tmp/test.png`, file exists
2. `test_export_rejects_compact_format` — `--export x.png --format compact` exits with error
3. `test_export_rejects_semantic_format` — same for semantic

## Key Design Decisions

### Cell-grid rendering (critical)

Naive rendering uses `len(text) * char_width` for positioning. But in DejaVu Sans Mono, block chars (`█` = 10px) and box-drawing (`━` = 10px) are wider than ASCII (`M` = 8px at 14pt). Solution: render char-by-char into fixed-width cells, like a real terminal emulator:

```python
cell_w = int(font.getlength("M"))
for ch in text:
    glyph_w = font.getlength(ch)
    offset = (cell_w - glyph_w) / 2  # center in cell
    draw.text((x + offset, y), ch, font=font, fill=fg)
    x += cell_w  # fixed advance
```

### Programmatic braille rendering (critical)

No system font renders braille characters properly in Pillow. Solution: detect braille range (U+2800–U+28FF), decode the bit pattern, draw actual dots as circles:

```python
BRAILLE_DOT_MAP = {
    0: (0, 0), 1: (0, 1), 2: (0, 2),
    3: (1, 0), 4: (1, 1), 5: (1, 2),
    6: (0, 3), 7: (1, 3),
}
```

Tuned parameters: r=0.25×cell_w, mx=0.10×cell_w, my=0.04×cell_h.

### Supersampling

Render at 2× font size, downscale with `Image.LANCZOS`. 2× is the sweet spot — crisp antialiasing, reasonable file size.

## Files Changed

| File | Action |
|------|--------|
| `src/csvplot/export.py` | **New** — ANSI parser + Pillow cell-grid PNG renderer |
| `src/csvplot/cli.py` | Add `--export` option to all 5 commands + Rich ANSI capture helper |
| `tests/test_export.py` | **New** — unit tests for ANSI parser, braille renderer, PNG output |
| `tests/test_export_integration.py` | **New** — CLI integration tests for `--export` flag |

## Verification

1. `uv run pytest` — all tests pass
2. `uv run csvplot bar -f data/titanic.csv -c Embarked --export /tmp/bar.png` — creates PNG, opens correctly
3. `uv run csvplot timeline -f data/projects.csv --x start_date --x end_date --y project --export /tmp/timeline.png` — braille segments visible
4. `uv run csvplot line -f data/temperatures.csv --x Date --y Temp --head 40 --export /tmp/line.png` — braille line visible
5. `uv run csvplot bubble -f data/titanic.csv --cols Cabin --cols Age --y Name --head 12 --export /tmp/bubble.png` — Rich table rendered
6. `uv run csvplot summarise -f data/titanic.csv --export /tmp/summarise.png` — Rich table rendered
7. `uv run csvplot bar -f data/titanic.csv -c Embarked --format compact --export /tmp/x.png` — errors cleanly
