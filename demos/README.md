# Demo GIF Generation

The demo GIFs in `assets/images/` are recorded using [VHS](https://github.com/charmbracelet/vhs) (a terminal recorder). Each GIF is produced from a `.tape` file that runs a `_sim.sh` script simulating a user typing commands with tab completion.

## Architecture

```
demos/
  lib.sh              # shared helpers: simulate_type, simulate_tab, PATH setup
  bar_sim.sh          # simulation script for bar chart demo
  bar.tape            # VHS tape that records bar_sim.sh into a GIF
  ...                 # same pattern for line, bubble, timeline, summarise, completion
scripts/
  generate_demos.sh   # runs all tapes in sequence, outputs to assets/images/
```

### Flow

1. `generate_demos.sh` adds `.venv/bin` to PATH and runs each `.tape` file through VHS
2. Each `.tape` hides the setup (`clear && bash demos/X_sim.sh`), then shows the simulated terminal session
3. Each `_sim.sh` sources `lib.sh` for helpers and simulates a user building a cplt command

## Simulation Rules

The sim scripts follow strict patterns to make demos look like a real user discovering cplt's features.

### Rule 1: Start with `--help`

Every plot demo starts by tab-completing the subcommand and showing `--help`, so viewers see all available flags before the command is built.

```bash
simulate_type "cplt "
simulate_tab "ba" "bar"
simulate_type " --help"
echo ""
cplt bar --help
sleep 2
```

### Rule 2: Flag tab completion

Flags the user "knows" are tab-completed from a short prefix. Type a few characters, pause, the rest appears instantly.

```bash
simulate_tab "--fi" "--file"
simulate_tab "--col" "--column"
simulate_tab "--wh" "--where"
```

### Rule 3: Per-directory file path completion

File paths complete in two steps matching real shell behavior — directory first, then filename.

```bash
simulate_tab "da" "data/"
simulate_tab "ti" "titanic.csv"
```

### Rule 4: Column discovery menus

The user doesn't know what columns exist. They hit tab, a completion menu appears showing all available columns, the prompt reprints, and they type their choice.

```bash
# pause as if hitting tab
sleep 1
echo ""
# show the completion menu
echo "Age          Cabin        Embarked     Fare         Name         Parch"
echo "PassengerId  Pclass       Sex          SibSp        Survived     Ticket"
# reprint prompt + command so far
printf '%s' "$PROMPT"
printf '%s' "cplt bar --file data/titanic.csv --column "
# user reads the menu, then types
sleep 2
simulate_type "Embarked"
```

After the first discovery, subsequent column args use `simulate_tab` with a prefix (the user has already seen what's available).

### Rule 5: `--where` value discovery

The `--where` flag has two levels of completion:

1. **Column discovery** — show `Col=` options so the user knows which columns can be filtered
2. **Value discovery** — after typing `Sex=`, show the actual values (`female`, `male`)

```bash
# Level 1: which columns can I filter?
sleep 1
echo ""
echo "Age=         Embarked=    Name=        PassengerId= Sex=         Survived="
printf '%s' "$PROMPT"
printf '%s' "cplt bar ... --where "
sleep 2
simulate_type "Sex="

# Level 2: what values does Sex have?
sleep 1
echo ""
echo "female  male"
printf '%s' "$PROMPT"
printf '%s' "cplt bar ... --where Sex="
sleep 2
simulate_type "female"
```

## lib.sh Helpers

| Function | Purpose |
|----------|---------|
| `simulate_type "text"` | Types text character-by-character (0.04s per char) |
| `simulate_tab "prefix" "full"` | Types prefix, pauses 0.5s, instantly prints the rest |
| `PROMPT` | The shell prompt string (`$ `) |

The lib also adds `.venv/bin` to PATH so `cplt` is available without manual activation.

## Generating GIFs

```bash
# all GIFs
bash scripts/generate_demos.sh

# single GIF
vhs demos/bar.tape
```

Requires [VHS](https://github.com/charmbracelet/vhs) and cplt installed in the project venv.

## Tape Configuration

All tapes share these VHS settings:

```
Set Shell "bash"
Set FontFamily "DejaVu Sans Mono"
Set FontSize 14
Set Width 1200       # (1400 for timeline/completion)
Set Height 600
Set Padding 20
Set Theme "Dracula"
Set TypingSpeed 0    # typing is handled by sim scripts, not VHS
```

The `Sleep` duration at the end of each tape must exceed the sim script runtime. Measure with `time bash demos/X_sim.sh` and add a 2s buffer.
