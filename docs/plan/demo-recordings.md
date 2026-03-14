# Demo Recordings — Plan for Repo Images

## Problem

Current repo images are generated/static and don't capture the real terminal
experience. We need high-fidelity demo images and GIFs that look like the
actual terminal output, for README and docs.

---

## Tool Comparison

### expect + asciinema (original plan)

**Pros:** Works, widely available, .cast format is shareable.

**Cons:**
- Two separate tools stitched together.
- Timing-based `pause`/`send` is fragile — if a command takes longer than
  expected, the recording desyncs.
- Tab completion timing is especially flaky with expect.
- .cast is not an image — needs a second conversion step (`agg` or
  `svg-term-cli`) to get PNG/GIF/SVG for the README.
- No built-in terminal size control (varies per machine).
- Debugging broken recordings is painful.

### vhs (Charm) — RECOMMENDED

`vhs` is purpose-built for creating terminal demos. Declarative `.tape` files,
direct GIF/PNG/WebM output, deterministic.

**Pros:**
- Single tool: tape file → GIF/PNG/WebM in one command.
- Declarative syntax — easy to read, version, and maintain.
- Built-in terminal size, font, theme, padding control.
- Typing simulation with configurable speed.
- `Sleep`, `Enter`, `Tab`, `Ctrl+C` are first-class.
- Deterministic — same tape always produces same output.
- No PS1/hostname leakage by design (isolated shell).

**Cons:**
- Requires `vhs` install (`go install` or brew/apt).
- Needs `ttyd` and `ffmpeg` as runtime deps.

**Install:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg
go install github.com/charmbracelet/vhs@latest

# macOS
brew install charmbracelet/tap/vhs
```

---

## Recommended Approach: vhs

### Tape file format

```tape
# demo_bar.tape
Output demo_bar.gif
Output demo_bar.png

Set Shell "bash"
Set FontFamily "DejaVu Sans Mono"
Set FontSize 14
Set Width 1200
Set Height 600
Set Padding 20
Set Theme "Dracula"

# Hide prompt customization
Hide
Type "export PS1='$ '"
Enter
Sleep 500ms
Show

# Demo command
Type "cplt bar -f data/titanic.csv -c Sex"
Sleep 500ms
Enter
Sleep 3s
```

### Key settings

| Setting | Value | Why |
|---------|-------|-----|
| FontFamily | DejaVu Sans Mono | Matches our export renderer |
| FontSize | 14 | Readable, matches terminal default |
| Width | 1200 | Wide enough for charts |
| Height | 600 | Tall enough for 30-40 line output |
| Theme | Dracula or custom | Dark theme consistent with export |
| Padding | 20 | Clean margins |

### Demo scenarios to record

| File | Command | Shows |
|------|---------|-------|
| `demo_bar.tape` | `cplt bar -f data/titanic.csv -c Sex` | Bar chart |
| `demo_bar_sort.tape` | `cplt bar -f data/titanic.csv -c Pclass --sort label` | Sorted bar |
| `demo_line.tape` | `cplt line -f data/temperatures.csv --x Date --y Temp` | Line chart |
| `demo_bubble.tape` | `cplt bubble -f data/titanic.csv --cols Cabin --cols Age --cols Embarked --y Name --head 20` | Bubble matrix |
| `demo_summarise.tape` | `cplt summarise -f data/titanic.csv` | Summary table |
| `demo_timeline.tape` | `cplt timeline -f data/timeplot.csv --x Start --x End --y Task` | Timeline/Gantt |
| `demo_completion.tape` | Tab completion flow | Shell completion |
| `demo_where.tape` | `cplt bar -f data/titanic.csv -c Pclass --where Sex=female` | Filtering |

### Generating

```bash
# Single demo
vhs demo_bar.tape

# All demos
for tape in demos/*.tape; do vhs "$tape"; done
```

### Output formats

- **GIF** — for README inline (GitHub renders GIFs natively)
- **PNG** — for docs, static screenshots (last frame)
- **WebM** — optional, smaller than GIF for web docs

---

## Improvements Over Original expect + asciinema Plan

| Aspect | expect + asciinema | vhs |
|--------|-------------------|-----|
| Timing | Fragile `sleep` based | Declarative `Sleep 2s` |
| Tab completion | Flaky, race conditions | First-class `Tab` command |
| Output format | .cast (needs conversion) | Direct GIF/PNG/WebM |
| Terminal size | Uncontrolled | `Set Width/Height` |
| Font control | None | `Set FontFamily/Size` |
| Theme | Whatever user has | `Set Theme` |
| Hostname leak | Manual PS1 hack | Isolated shell by default |
| Debugging | Replay .cast and guess | Edit tape, re-run |
| Deps | expect + asciinema + agg | vhs (+ ffmpeg) |
| Reproducibility | Timing-dependent | Deterministic |

---

## Original expect Plan — Fixes If You Still Want It

If vhs isn't an option, here's the corrected expect approach:

### Fix 1: Use `expect` not `sleep` for synchronization

```expect
# BAD: timing-based
send -- "cplt bar -f data/titanic.csv -c Sex\r"
pause 3

# GOOD: wait for prompt
send -- "cplt bar -f data/titanic.csv -c Sex\r"
expect "demo$"
```

### Fix 2: Lock terminal size

```expect
spawn bash --noprofile --norc -i
send -- "stty rows 40 cols 120\r"
send -- "export PS1='$ '\r"
send -- "export COLUMNS=120 LINES=40\r"
```

And when recording:
```bash
asciinema rec demo.cast --cols 120 --rows 40 --command "expect ./demo.exp"
```

### Fix 3: Convert .cast to image

```bash
# Install agg (asciinema gif generator)
cargo install --git https://github.com/asciinema/agg

# .cast → GIF
agg demo.cast demo.gif --cols 120 --rows 40 --font-family "DejaVu Sans Mono"

# Or: svg-term-cli for SVG
npm install -g svg-term-cli
svg-term --in demo.cast --out demo.svg --window --width 120 --height 40
```

### Fix 4: Add cplt completion to the session

```expect
send -- "eval \"$(cplt --show-completion bash)\"\r"
expect "demo$"
```

### Fix 5: Demo actual cplt commands

```expect
# Bar chart demo
send -- "cplt bar -f data/titanic.csv -c Sex\r"
expect "demo$"
sleep 1

# Tab completion demo
send -- "cplt bar -f data/titanic.csv -c \t"
sleep 1
send -- "\t"
sleep 2
send -- "\003"
```

---

## Recommendation

Use **vhs** for demo recordings. It solves every pain point of the expect
approach with less code and better output. Save the Pillow `--export` renderer
for the user-facing CLI feature (different use case).

### Two separate concerns

1. **Repo demos** (this doc) → vhs tape files → GIF/PNG for README
2. **User `--export` flag** (export-png.md) → Pillow renderer → PNG at user's path
