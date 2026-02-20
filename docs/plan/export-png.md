# Export PNG — Research Findings

## Goal

Add `--export <path>` to csvplot that writes a PNG as close to the terminal
screen as possible. Must be cross-OS, lightweight, zero new dependencies.

---

## Approaches Evaluated

### 1. Rich Console → SVG → cairosvg → PNG

**How it works:** Feed ANSI output through `Rich.Text.from_ansi()`, record with
`Console(record=True)`, call `console.export_svg()`, convert to PNG via cairosvg.

**Result: REJECTED**

- Braille characters (U+2800–U+28FF) render as `□` squares — the SVG font
  lacks those glyphs.
- Box-drawing characters (`━`, `┃`, `┏`) also render as squares.
- Bar chart block chars (`█`) render as squares.
- Crashes with `CAIRO_STATUS_INVALID_SIZE` on large outputs (>~500 lines).
- Pulls in cairosvg → cffi → pycparser (heavy dependency chain).

### 2. ansitoimg library → SVG → PNG

**How it works:** Third-party lib that wraps Rich's SVG export with themes.

**Result: REJECTED**

- Identical output to approach 1 (uses Rich under the hood).
- Same broken glyph rendering for braille/block/box chars.
- Same cairo crash on large outputs.
- Additionally pulls in playwright (headless browser!) as a dependency.

### 3. Pillow direct ANSI → PNG (SELECTED)

**How it works:** Parse ANSI escape codes, render char-by-char into a Pillow
Image using a monospace font, with 2× supersampling + LANCZOS downscale.

**Result: SELECTED — best across all chart types**

- Pillow is already a dependency (zero new deps).
- Cross-OS: DejaVu Sans Mono available everywhere.
- Handles arbitrarily large outputs (no cairo size limits).
- File sizes 3–10× smaller than SVG approaches.

### Other approaches considered but not prototyped

- **termtosvg**: Reconstructs terminal state, close but not pixel-identical.
- **carbon-now-sh**: Completely re-renders with its own styling.
- **ANSI → HTML converters**: Approximate styling, not accurate.
- **Native OS screenshot**: Pain to configure per-OS, unreliable.
- **freeze**: Re-renders with its own renderer, not the terminal's font engine.

---

## Pillow Renderer — Key Design Decisions

### Cell-grid rendering (critical fix)

**Problem:** Naive rendering uses `len(text) * char_width` for positioning.
But in DejaVu Sans Mono, block chars (`█` = 10px) and box-drawing (`━` = 10px)
are wider than ASCII (`M` = 8px at 14pt). This breaks column alignment.

**Solution:** Render **char-by-char into fixed-width cells**, like a real
terminal emulator:

```python
cell_w = int(font.getlength("M"))
for ch in text:
    glyph_w = font.getlength(ch)
    offset = (cell_w - glyph_w) / 2  # center in cell
    draw.text((x + offset, y), ch, font=font, fill=fg)
    x += cell_w  # fixed advance
```

### Programmatic braille rendering (critical fix)

**Problem:** No system font (DejaVu, Liberation, Ubuntu Mono, Noto Mono)
renders braille characters properly in Pillow. All show `□` squares regardless
of font size (tested 12–32px) or supersample level (2×, 3×).

**Solution:** Detect braille range (U+2800–U+28FF), decode the bit pattern,
draw actual dots as circles:

```python
# Each braille char encodes 8 dots in a 2×4 grid
# Codepoint = 0x2800 + dot_bits
BRAILLE_DOT_MAP = {
    0: (0, 0), 1: (0, 1), 2: (0, 2),
    3: (1, 0), 4: (1, 1), 5: (1, 2),
    6: (0, 3), 7: (1, 3),
}
```

**Tuned parameters (B balanced):**

| Parameter | Value | Notes |
|-----------|-------|-------|
| dot_radius | 0.25 × cell_w | Dense enough to merge in filled areas |
| margin_x | 0.10 × cell_w | Tight horizontal gaps between cells |
| margin_y | 0.04 × cell_h | Dots span nearly full cell height |

**Parameter sweep results:**

- `r=0.14, mx=0.20, my=0.08` — too sparse, reads as scatter plot
- `r=0.20, mx=0.12, my=0.05` — visible dots, some texture (option A)
- **`r=0.25, mx=0.10, my=0.04`** — sweet spot, reads as line (option B) ✓
- `r=0.28, mx=0.05, my=0.02` — nearly solid, loses braille character (option C)

### Supersampling

Render at 2× font size, then downscale with `Image.LANCZOS`:

```python
img = Image.new("RGB", (w * 2, h * 2), BG)
# ... render at 2× ...
img = img.resize((w, h), Image.LANCZOS)
```

- 2× is the sweet spot — crisp antialiasing, reasonable file size.
- 3× is marginally crisper but diminishing returns.

---

## Rendering Config — Final Settings

| Parameter | Value |
|-----------|-------|
| Font | DejaVu Sans Mono (system) |
| Base font size | 16px |
| Supersample factor | 2× |
| Background | `#1E1E1E` (30, 30, 30) |
| Default foreground | `#CCCCCC` (204, 204, 204) |
| Padding | 16px |
| Line height | natural (ascent + descent, no multiplier) |
| Downscale filter | LANCZOS |

---

## Per-Chart-Type Strategy

| Chart type | Export method | Quality |
|------------|-------------|---------|
| bar | ANSI → Pillow cell grid | Excellent — solid blocks, clean axes |
| bubble | ANSI → Pillow cell grid | Excellent — `●` dots, table borders perfect |
| summarise | ANSI → Pillow cell grid | Excellent — Rich tables fully readable |
| timeline | ANSI → Pillow cell grid + braille | Good — braille dots show segment patterns |
| **line** | **Native Pillow draw from LineSpec** | **Best — smooth lines, pixel resolution** |

### Line chart: native rendering

The braille approach has a fundamental resolution ceiling — each character cell
is a 2×4 dot grid, so vertical resolution is locked to 8 dots per cell height.
Even at 350 columns wide, the chart still looks like a dot matrix.

For the line chart export, bypass terminal rendering entirely and draw directly
from `LineSpec` data using Pillow's `draw.line()`:

- Same dark theme and PALETTE_RGB colors for consistency
- Actual smooth lines at pixel resolution
- Grid lines, axis labels, legend — all drawn natively
- Configurable width/height (default ~1200×600)
- Multi-series support with color cycling and legend

---

## ANSI Color Parsing

Supports the full range plotext/Rich emit:

- SGR basic colors (30–37, 90–97 foreground; 40–47, 100–107 background)
- 256-color mode (`38;5;N` / `48;5;N`)
- Truecolor mode (`38;2;R;G;B` / `48;2;R;G;B`)
- Bold → bright color variant mapping
- Reset (`0`), default fg (`39`), default bg (`49`)

---

## Font Metrics (DejaVu Sans Mono)

| Size | M width | █ width | ━ width | ● width | Ascent | Descent | Line height |
|------|---------|---------|---------|---------|--------|---------|-------------|
| 12 | 7 | 9 | 9 | 8 | 12 | 3 | 15 |
| 14 | 8 | 10 | 10 | 9 | 13 | 4 | 17 |
| **16** | **10** | **11** | **11** | **10** | **15** | **4** | **19** |
| 18 | 11 | 13 | 13 | 11 | 17 | 5 | 22 |
| 20 | 12 | 14 | 14 | 12 | 19 | 5 | 24 |
| 24 | 14 | 16 | 16 | 15 | 23 | 6 | 29 |

Note: `█` and `━` are 1–2px wider than `M` at every size — this is why
cell-grid rendering (fixed advance from M width) is essential.

---

## Native OS Screenshot Proposal (Terminal-Accurate Mode)

If the goal is "exact terminal feel" instead of text re-rendering, add an
optional export backend that captures a real terminal window using OS-native
screenshot tools.

### Proposed CLI

- `--export <path>`: output PNG path
- `--export-engine pillow|native`: rendering backend (`pillow` default)
- `--terminal-cmd <cmd>`: terminal app override for native mode
- `--capture-delay-ms <n>`: wait before screenshot (default 250)

Example:

```bash
csvplot line data.csv --x date --y value \
  --export chart.png \
  --export-engine native
```

### High-Level Flow

1. Render chart normally (ANSI output).
2. Write output to a temp script/command that prints and waits briefly.
3. Launch a dedicated terminal window (fixed size/font profile).
4. Detect terminal window rectangle.
5. Capture that rectangle with native screenshot command.
6. Save PNG to `--export` path, close helper window.

This captures the terminal's actual font engine and glyph rasterization.

### OS-Specific Backends

| OS | Window bounds | Screenshot command | Notes |
|----|---------------|--------------------|-------|
| macOS | `osascript` (Terminal/iTerm window bounds) | `screencapture -R x,y,w,h out.png` | Requires Screen Recording permission for terminal/app |
| Windows | PowerShell + Win32 `GetWindowRect` | PowerShell `.NET Bitmap + CopyFromScreen` | No extra dependency; works on Windows Terminal/ConHost |
| Linux (X11) | `xdotool`/`xwininfo` | `import -window` or `maim` | Reliable in X11 sessions |
| Linux (Wayland) | compositor tools (`grim`) or portal | `grim -g "x,y wxh"` | Varies by compositor; fallback required |

### Linux Strategy (important)

Linux has no single screenshot command that is guaranteed everywhere. Use a
capability probe and fallback chain:

1. Wayland + `grim` available -> use `grim`
2. X11 + `import` available -> use `import`
3. X11 + `maim` available -> use `maim`
4. Else fail with actionable message listing missing tools

This keeps the implementation native but practical.

### Recommended Implementation Shape

- Add `src/csvplot/export_native.py` with:
- `capture_native_png(ansi_text: str, out_path: Path, opts: NativeOpts) -> None`
- Internal providers:
- `MacCaptureProvider`
- `WindowsCaptureProvider`
- `LinuxCaptureProvider`
- Provider interface:
- `check_available()`
- `open_terminal_and_get_bounds(...)`
- `capture(bounds, out_path)`

### Operational Constraints

- Requires a GUI desktop session (not headless SSH/CI).
- Window managers/compositors may animate; delay is needed.
- macOS users may need one-time permissions.
- Native captures can include subtle OS chrome differences.

### Recommended Product Decision

Use a hybrid model:

- Keep `pillow` as default for deterministic, dependency-light exports.
- Add `native` as opt-in for users who want authentic terminal rasterization.
- Emit clear diagnostics when native tooling is unavailable.

This avoids regressions for CI/server users while enabling the terminal-perfect
path on local desktops.
