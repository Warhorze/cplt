# Plan: Standardize demo GIF generation with simulation scripts

## Feedback (addressed)

1. **Bar --where tab completion** — bar_sim.sh now shows `--where` tab discovery with `col=` menu and value completions (same pattern as completion_sim.sh)
2. **Flag tab feels jittery** — increased `simulate_tab` pause from 0.3s to 0.5s and added a subtle pause after completion appears, making `--fi → --file` feel like a natural tab-complete rather than a glitch
3. **Typing speed too fast** — increased `simulate_type` sleep from 0.02s to 0.05s per character
4. **Show subcommand completion + --help** — each sim script now starts by showing the subcommand tab-completed from `csvplot` and ends (or starts) with a brief `--help` display so users see all available options
5. **File paths per-directory** — file path completion now goes `data/` first (tab from `da`), then `ti → titanic.csv` as a second tab, matching real shell behavior

## Context

The demo sim scripts simulate typing CLI commands for VHS recordings. They showcase tab completion — a key csvplot feature. All flags, column names, and file paths show simulated tab completion (type a prefix, pause, rest appears instantly). The bar chart also has distinct colors per bar (already done).

**Key insight:** The user knows the flags (`--file`, `--x`, `--y`) but **doesn't know** the column names in the CSV. Tab completion lets them discover what's available. Demos should showcase this discoverability by showing the full completion menu for column names, then selecting from it.

**Already done:**
- [x] Bar chart: PALETTE-cycled colors (TDD — test + fix committed)
- [x] All `*_sim.sh` scripts exist and source `demos/lib.sh`
- [x] All `.tape` files use the Hide/Show simulation pattern
- [x] `demos/lib.sh` has `simulate_type()` and `simulate_tab(prefix, full)`
- [x] `scripts/generate_demos.sh` has `reset` + `sleep 1` between tapes

## Simulation patterns

Three patterns, used depending on what the user "knows":

### Pattern A: `simulate_tab` — for known tokens (flags, known columns)
User knows the flag name, types a prefix, tab completes the rest.
```bash
simulate_tab "--file" "--file"    # type "--f", pause, "ile" appears
```

### Pattern B: menu discovery — for unknown tokens (columns, where values)
User doesn't know the options, hits tab to see all of them, reads the menu, then types to select.
```bash
sleep 1; echo ""
echo "Date  Temp"
printf '%s' "$PROMPT"
printf '%s' "csvplot line --file data/temperatures.csv --x "
sleep 2
simulate_type "Date"
```

### Pattern C: directory-then-file — for file paths
Matches real shell behavior: tab-complete the directory first, then the file.
```bash
simulate_tab "da" "data/"
simulate_tab "ti" "titanic.csv"
```

## Completion reference

| File | All columns | Date columns (for timeline `--x`) |
|------|------------|----------------------------------|
| `data/titanic.csv` | Age, Cabin, Embarked, Fare, Name, Parch, PassengerId, Pclass, Sex, SibSp, Survived, Ticket | (none) |
| `data/temperatures.csv` | Date, Temp | Date |
| `data/projects.csv` | project, team, start_date, end_date, status | start_date, end_date |

Data files in `data/`: `projects.csv`, `temperatures.csv`, `timeplot2.csv`, `timeplot.csv`, `titanic.csv`

## 1. `demos/lib.sh` changes

- `simulate_type`: sleep 0.02 → 0.05 per character (slower, more readable)
- `simulate_tab`: increase pause from 0.3s to 0.5s, post-completion pause from 0.4s to 0.5s

## 2. Sim script updates

Each sim script follows this structure:
1. Show subcommand tab-completion: `csvplot ` → tab → `bar` (from `ba` prefix)
2. Show `--help` output briefly so user sees available options
3. Build the actual command with flag/column/file tab completions
4. File paths use per-directory completion (Pattern C)
5. Bar `--where` shows column= discovery menu and value= discovery menu

### `demos/bar_sim.sh`
- Subcommand tab: `simulate_tab "ba" "bar"`
- Show `csvplot bar --help` output
- Per-directory file: `simulate_tab "da" "data/"` then `simulate_tab "ti" "titanic.csv"`
- Column discovery menu for `--column`
- `--where` discovery: show `col=` menu, type `Sex=`, show value menu, select `female`
- Tab-complete `--labels`

### `demos/line_sim.sh`
- Subcommand tab: `simulate_tab "li" "line"`
- Show `csvplot line --help` output
- Per-directory file: `simulate_tab "da" "data/"` then `simulate_tab "te" "temperatures.csv"`
- Column discovery for `--x`, tab-complete `--y Temp`

### `demos/bubble_sim.sh`
- Subcommand tab: `simulate_tab "bu" "bubble"`
- Show `csvplot bubble --help` output
- Per-directory file path
- Column discovery for `--cols`, tab-complete subsequent cols/y/color

### `demos/timeline_sim.sh`
- Subcommand tab: `simulate_tab "ti" "timeline"`
- Show `csvplot timeline --help` output
- Per-directory file: `da` → `data/`, `pr` → `projects.csv`
- Date column discovery for `--x`, all column discovery for `--y`

### `demos/summarise_sim.sh`
- Subcommand tab: `simulate_tab "su" "summarise"`
- Show `csvplot summarise --help` output
- Per-directory file path

### `demos/completion_sim.sh`
- Subcommand tab + per-directory file path
- Column discovery, --where col= discovery, value= discovery
- Same as current but with updated patterns

## 3. Bar chart: distinct colors per bar (DONE)

Already committed.

## 4. Update tape Sleep durations

After implementing, measure each sim script with `time bash demos/X_sim.sh` and set tape Sleep to measured + 2s buffer. Scripts will be longer due to slower typing and --help displays.

## File changes summary

| File | Action |
|------|--------|
| `demos/lib.sh` | Slower typing (0.05s), smoother tab (0.5s pause) |
| `demos/bar_sim.sh` | Subcommand tab, --help, per-dir file, --where discovery |
| `demos/line_sim.sh` | Subcommand tab, --help, per-dir file |
| `demos/bubble_sim.sh` | Subcommand tab, --help, per-dir file |
| `demos/timeline_sim.sh` | Subcommand tab, --help, per-dir file |
| `demos/summarise_sim.sh` | Subcommand tab, --help, per-dir file |
| `demos/completion_sim.sh` | Subcommand tab, per-dir file, updated patterns |
| `demos/*.tape` | Adjusted Sleep durations |

## Verification

1. `time bash demos/bar_sim.sh` — measure actual runtime for each script
2. Each sim script runs cleanly with visible column discovery menus
3. Adjust tape Sleep durations to measured runtime + 2s buffer
4. Run each VHS tape individually: `vhs demos/bar.tape` etc.
