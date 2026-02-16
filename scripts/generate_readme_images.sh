#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMG_DIR="$ROOT_DIR/assets/images"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

RENDER_PYTHON="$PYTHON_BIN"
if ! "$RENDER_PYTHON" -c "import PIL" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1 && python3 -c "import PIL" >/dev/null 2>&1; then
    RENDER_PYTHON="python3"
  else
    echo "Pillow (PIL) is required to render PNG images." >&2
    exit 1
  fi
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$IMG_DIR"

run_csvplot() {
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON_BIN" -m csvplot "$@"
}

run_csvplot timeline -f "$ROOT_DIR/data/timeplot.csv" \
  --x DH_PV_STARTDATUM --x DH_PV_EINDDATUM \
  --x EN_START_DATETIME --x EA_END_DATETIME \
  --y DH_FACING_NUMMER --color SH_ARTIKEL_S1 \
  --head 12 --marker 2025-01-22 --marker-label wissel-datum \
  --format visual > "$TMP_DIR/timeline.txt"

run_csvplot bar -f "$ROOT_DIR/data/titanic.csv" \
  --column Sex --format visual > "$TMP_DIR/bar.txt"

run_csvplot line -f "$ROOT_DIR/data/temperatures.csv" \
  --x Date --y Temp --head 40 --title "Melbourne Min Temp" \
  --format visual > "$TMP_DIR/line.txt"

run_csvplot bubble -f "$ROOT_DIR/data/titanic.csv" \
  --cols Cabin --cols Age --cols Embarked --y Name --head 12 \
  --format visual > "$TMP_DIR/bubble.txt"

"$RENDER_PYTHON" "$ROOT_DIR/scripts/render_terminal_png.py" \
  "$TMP_DIR/timeline.txt" "$IMG_DIR/timeline.png" \
  --title "csvplot timeline output"

"$RENDER_PYTHON" "$ROOT_DIR/scripts/render_terminal_png.py" \
  "$TMP_DIR/bar.txt" "$IMG_DIR/bar.png" \
  --title "csvplot bar output"

"$RENDER_PYTHON" "$ROOT_DIR/scripts/render_terminal_png.py" \
  "$TMP_DIR/line.txt" "$IMG_DIR/line.png" \
  --title "csvplot line output"

"$RENDER_PYTHON" "$ROOT_DIR/scripts/render_terminal_png.py" \
  "$TMP_DIR/bubble.txt" "$IMG_DIR/bubble.png" \
  --title "csvplot bubble output"

echo "README images updated in $IMG_DIR"
