#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
else
  PYTHON_BIN="python"
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

PASS_COUNT=0
FAIL_COUNT=0

run_cplt() {
  PYTHONPATH="$ROOT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
    "$PYTHON_BIN" -m cplt "$@"
}

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  echo "PASS: $1"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo "FAIL: $1"
}

run_ok() {
  local name="$1"
  shift

  local out_file="$TMP_DIR/${name// /_}.out"
  if run_cplt "$@" >"$out_file" 2>&1; then
    pass "$name"
  else
    fail "$name"
    sed -n '1,120p' "$out_file"
  fi
}

run_expected_fail() {
  local name="$1"
  local expected_text="$2"
  shift 2

  local out_file="$TMP_DIR/${name// /_}.out"
  set +e
  run_cplt "$@" >"$out_file" 2>&1
  local code=$?
  set -e

  if [[ $code -ne 0 ]] && grep -Fq "$expected_text" "$out_file"; then
    pass "$name"
  else
    fail "$name"
    sed -n '1,120p' "$out_file"
    echo "Expected non-zero exit and message containing: $expected_text"
  fi
}

echo "Running cplt CLI smoke flow..."

run_ok "help" --help

run_ok "timeline compact" \
  timeline -f "$ROOT_DIR/data/projects.csv" \
  --x start_date --x end_date --y project --head 8 --format compact

run_ok "bar compact" \
  bar -f "$ROOT_DIR/data/titanic.csv" \
  --column Sex --format compact

run_ok "line compact" \
  line -f "$ROOT_DIR/data/temperatures.csv" \
  --x Date --y Temp --head 20 --format compact

run_ok "bubble compact" \
  bubble -f "$ROOT_DIR/data/titanic.csv" \
  --cols Cabin --cols Age --cols Embarked --y Name --head 8 --format compact

run_ok "summarise" \
  summarise -f "$ROOT_DIR/data/projects.csv"

run_expected_fail "invalid column error" "Column 'NotAColumn' not found" \
  bar -f "$ROOT_DIR/data/titanic.csv" --column NotAColumn

echo
echo "Smoke summary: $PASS_COUNT passed, $FAIL_COUNT failed"

if [[ $FAIL_COUNT -ne 0 ]]; then
  exit 1
fi
