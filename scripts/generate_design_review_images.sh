#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/assets/review"
RAW_DIR="$OUT_DIR/raw"
IMG_DIR="$OUT_DIR/images"
UX_LOG="$OUT_DIR/ux-flow.log"
REPORT_FILE="$OUT_DIR/REPORT.md"
SCENARIOS_FILE="$OUT_DIR/SCENARIOS.md"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

die_with_setup_hint() {
  echo "$1" >&2
  echo "Install dependencies with: uv sync --extra dev" >&2
  exit 1
}

if ! PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
  "$PYTHON_BIN" -c "import cplt.cli" >/dev/null 2>&1; then
  die_with_setup_hint "Unable to run cplt with '$PYTHON_BIN'."
fi

if ! "$PYTHON_BIN" -c "import plotext, rich, typer" >/dev/null 2>&1; then
  die_with_setup_hint "Missing runtime dependencies for '$PYTHON_BIN' (plotext/rich/typer)."
fi

mkdir -p "$RAW_DIR" "$IMG_DIR"
rm -f "$RAW_DIR"/*.txt "$IMG_DIR"/*.png "$UX_LOG"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

SCENARIO_LINK_ROWS="$TMP_DIR/scenario-link-rows.md"
SCENARIO_REPORT_ROWS="$TMP_DIR/scenario-report-rows.md"
SCENARIO_CMD_ROWS="$TMP_DIR/scenario-cmd-rows.md"
CHECK_ROWS="$TMP_DIR/check-rows.md"
> "$SCENARIO_LINK_ROWS"
> "$SCENARIO_REPORT_ROWS"
> "$SCENARIO_CMD_ROWS"
> "$CHECK_ROWS"

run_cplt() {
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON_BIN" -m cplt "$@"
}

log_step() {
  local title="$1"
  echo "== $title ==" | tee -a "$UX_LOG"
}

record_scenario() {
  local group="$1"
  local slug="$2"
  local purpose="$3"
  shift 3
  local cmd_display
  cmd_display="cplt $(printf '%q ' "$@")"
  cmd_display="${cmd_display% }"

  printf '| %s | [%s.png](images/%s.png) | [visual](raw/%s.visual.txt) / [compact](raw/%s.compact.txt) / [semantic](raw/%s.semantic.txt) | %s |\n' \
    "$group" "$slug" "$slug" "$slug" "$slug" "$slug" "$purpose" >> "$SCENARIO_LINK_ROWS"

  printf '| %s | [%s.png](images/%s.png) | [visual](raw/%s.visual.txt) / [compact](raw/%s.compact.txt) / [semantic](raw/%s.semantic.txt) | `%s` | %s |\n' \
    "$group" "$slug" "$slug" "$slug" "$slug" "$slug" "$cmd_display" "$purpose" >> "$SCENARIO_REPORT_ROWS"

  printf '| %s | %s | `%s` | %s |\n' \
    "$group" "$slug" "$cmd_display" "$purpose" >> "$SCENARIO_CMD_ROWS"
}

capture_scenario() {
  local group="$1"
  local slug="$2"
  local title="$3"
  local purpose="$4"
  shift 4

  log_step "$group :: $slug"
  run_cplt "$@" --format visual --export "$IMG_DIR/${slug}.png" > "$RAW_DIR/${slug}.visual.txt"
  run_cplt "$@" --format compact > "$RAW_DIR/${slug}.compact.txt"
  run_cplt "$@" --format semantic > "$RAW_DIR/${slug}.semantic.txt"

  record_scenario "$group" "$slug" "$purpose" "$@"
}

append_diff_check() {
  local label="$1"
  local a="$2"
  local b="$3"
  if cmp -s "$a" "$b"; then
    printf -- '- %s: FAIL (outputs are identical)\n' "$label" >> "$CHECK_ROWS"
  else
    printf -- '- %s: PASS (outputs differ)\n' "$label" >> "$CHECK_ROWS"
  fi
}

log_step "timeline scenario matrix"
capture_scenario "timeline" "timeline_layers_color_vline" "timeline layers color vline" \
  "2-layer timeline with color legend and reference line" \
  timeline -f "$ROOT_DIR/data/timeplot.csv" \
  --x DH_PV_STARTDATUM --x DH_PV_EINDDATUM \
  --x EN_START_DATETIME --x EA_END_DATETIME \
  --y DH_FACING_NUMMER --color SH_ARTIKEL_S1 \
  --head 12 --vline 2025-01-22 --label wissel-datum

capture_scenario "timeline" "timeline_dot_window" "timeline dot window" \
  "dot markers plus view window clipping" \
  timeline -f "$ROOT_DIR/data/timeplot.csv" \
  --x DH_PV_STARTDATUM --x DH_PV_EINDDATUM \
  --y DH_FACING_NUMMER --dot EN_START_DATETIME \
  --head 12 --from 2024-01-01 --to 2025-12-31

log_step "bar scenario matrix"
capture_scenario "bar" "bar_labels_value" "bar labels value" \
  "value sort baseline distribution" \
  bar -f "$ROOT_DIR/data/titanic.csv" -c Sex --sort value

capture_scenario "bar" "bar_horizontal_top_label" "bar horizontal top label" \
  "horizontal top-N with label sort" \
  bar -f "$ROOT_DIR/data/titanic.csv" -c Embarked --sort label --top 3 --horizontal

log_step "line scenario matrix"
capture_scenario "line" "line_single_temp" "line single series" \
  "single-series temperature trend" \
  line -f "$ROOT_DIR/data/temperatures.csv" --x Date --y Temp --head 120

capture_scenario "line" "line_multi_color" "line multi color" \
  "multi-y line grouped by color column" \
  line -f "$ROOT_DIR/data/timeplot.csv" \
  --x DH_PV_STARTDATUM --y MH_AANTAL_FACINGS --y MH_AANTAL_PER_FACING \
  --color SH_ARTIKELSOORT --head 120

log_step "bubble scenario matrix"
capture_scenario "bubble" "bubble_base" "bubble base matrix" \
  "baseline matrix for compare/diff checks" \
  bubble -f "$ROOT_DIR/data/titanic.csv" --cols Cabin --cols Age --cols Embarked --y Name --head 12

capture_scenario "bubble" "bubble_color" "bubble color matrix" \
  "row color encoding and legend" \
  bubble -f "$ROOT_DIR/data/titanic.csv" --cols Cabin --cols Age --cols Embarked --y Name --color Pclass --head 12

capture_scenario "bubble" "bubble_sort_fill" "bubble sort fill" \
  "row reorder by fill rate" \
  bubble -f "$ROOT_DIR/data/titanic.csv" --cols Cabin --cols Age --cols Embarked --y Name --sort fill --head 12

capture_scenario "bubble" "bubble_grouped_base" "bubble grouped base" \
  "group-by aggregation baseline" \
  bubble -f "$ROOT_DIR/data/titanic.csv" --cols Cabin --cols Age --cols Embarked --y Name --group-by Sex --top 3

capture_scenario "bubble" "bubble_grouped_sorted" "bubble grouped sorted" \
  "group-by with sort fill" \
  bubble -f "$ROOT_DIR/data/titanic.csv" --cols Cabin --cols Age --cols Embarked --y Name --group-by Sex --top 3 --sort fill

capture_scenario "bubble" "bubble_grouped_transpose" "bubble grouped transpose" \
  "group-by with transpose" \
  bubble -f "$ROOT_DIR/data/titanic.csv" --cols Cabin --cols Age --cols Embarked --y Name --group-by Sex --top 3 --transpose

capture_scenario "bubble" "bubble_encode_base" "bubble encode base" \
  "encoded columns without transpose" \
  bubble -f "$ROOT_DIR/data/titanic.csv" --cols Cabin --cols Embarked --y Name --encode --top 8 --head 20

capture_scenario "bubble" "bubble_encode_transpose" "bubble encode transpose" \
  "encoded columns with transpose" \
  bubble -f "$ROOT_DIR/data/titanic.csv" --cols Cabin --cols Embarked --y Name --encode --top 8 --head 20 --transpose

log_step "visual diff checks"
append_diff_check "Bubble --color changes visual output" \
  "$RAW_DIR/bubble_base.visual.txt" "$RAW_DIR/bubble_color.visual.txt"
append_diff_check "Bubble grouped sort changes compact output" \
  "$RAW_DIR/bubble_grouped_base.compact.txt" "$RAW_DIR/bubble_grouped_sorted.compact.txt"
append_diff_check "Bubble encode transpose changes compact output" \
  "$RAW_DIR/bubble_encode_base.compact.txt" "$RAW_DIR/bubble_encode_transpose.compact.txt"

RUN_UX_TESTS="${RUN_UX_TESTS:-1}"
UX_FLOW_CHECK="SKIP (set RUN_UX_TESTS=1 to run)"
if [[ "$RUN_UX_TESTS" == "1" ]]; then
  log_step "combination-first ux flow"
  if UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ux/test_bubble_combinations.py -q >> "$UX_LOG" 2>&1 \
    && UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ux/test_scale_ux.py -q >> "$UX_LOG" 2>&1 \
    && UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ux/test_timeline_combinations.py -q >> "$UX_LOG" 2>&1 \
    && UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ux/test_bar_combinations.py -q >> "$UX_LOG" 2>&1 \
    && UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ux/test_line_combinations.py -q >> "$UX_LOG" 2>&1 \
    && UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ux/test_summarise_combinations.py -q >> "$UX_LOG" 2>&1 \
    && UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ux/ -q -rXx >> "$UX_LOG" 2>&1; then
    UX_FLOW_CHECK="PASS"
  else
    UX_FLOW_CHECK="FAIL (see ux-flow.log)"
  fi
fi

cat > "$SCENARIOS_FILE" <<EOF2
# Design Review Scenario Manifest

## Purpose

- SCENARIOS.md defines what to run: canonical scenario list, exact commands, and intent.
- REPORT.md shows what was produced from this run: artifact links, previews, and check results.

Generated by:

\`bash scripts/generate_design_review_images.sh\`

Each scenario is run in all formats (visual, compact, semantic), with PNG rendering from visual output.

| Group | Slug | Command | Purpose |
|---|---|---|---|
$(cat "$SCENARIO_CMD_ROWS")
EOF2

GENERATED_AT="$(date -u +'%Y-%m-%d %H:%M:%S UTC')"

cat > "$REPORT_FILE" <<EOF3
# Design Review Artifacts

## Purpose

- REPORT.md is run output: generated images/raw files plus automated check outcomes.
- SCENARIOS.md is the scenario spec: exact commands and intent for each scenario.

Generated: $GENERATED_AT

This folder is generated by:

\`\`\`bash
bash scripts/generate_design_review_images.sh
\`\`\`

## Scenario Artifacts

| Group | Visual PNG | Raw outputs | Command | Why this exists |
|---|---|---|---|---|
$(cat "$SCENARIO_REPORT_ROWS")

See full scenario definitions in [SCENARIOS.md](SCENARIOS.md).

## Visual Preview
$(for img in $(find "$IMG_DIR" -maxdepth 1 -type f -name '*.png' -printf '%f\n' | sort); do echo "![${img%.*}](images/$img)"; done)

Raw command outputs are in \`raw/\`.
UX test flow output is in \`ux-flow.log\`.

## Automated Checks

$(cat "$CHECK_ROWS")
- Combination-first UX flow: $UX_FLOW_CHECK

## UX Flow Used

1. \`tests/ux/test_bubble_combinations.py\`
2. \`tests/ux/test_scale_ux.py\`
3. \`tests/ux/test_timeline_combinations.py\`
4. \`tests/ux/test_bar_combinations.py\`
5. \`tests/ux/test_line_combinations.py\`
6. \`tests/ux/test_summarise_combinations.py\`
7. \`tests/ux/ -rXx\`
EOF3

echo "Design review artifacts updated in $OUT_DIR"
