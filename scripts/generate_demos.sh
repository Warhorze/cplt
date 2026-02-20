#!/usr/bin/env bash
# Generate demo GIFs from vhs tape files.
# Usage: bash scripts/generate_demos.sh

set -uo pipefail

if ! command -v vhs &>/dev/null; then
    echo "Error: vhs is not installed."
    echo "Install it with: go install github.com/charmbracelet/vhs@latest"
    echo "Or on macOS:     brew install charmbracelet/tap/vhs"
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Prefer project virtualenv binaries when present (vhs shell inherits PATH).
if [[ -d "$REPO_ROOT/.venv/bin" ]]; then
    export PATH="$REPO_ROOT/.venv/bin:$PATH"
fi

if ! command -v csvplot &>/dev/null; then
    echo "Error: csvplot is not available on PATH."
    echo "Try one of:"
    echo "  source .venv/bin/activate && pip install -e ."
    echo "  pip install -e ."
    exit 1
fi

mkdir -p assets/images

shopt -s nullglob
tapes=(demos/*.tape)
if [[ ${#tapes[@]} -eq 0 ]]; then
    echo "No tape files found in demos/"
    exit 1
fi

failed=()
for tape in "${tapes[@]}"; do
    name="$(basename "$tape" .tape)"
    echo "Recording ${name}..."
    if vhs "$tape"; then
        echo "  -> assets/images/${name}.gif"
    else
        echo "  !! failed to record ${name}"
        failed+=("$name")
    fi
    # VHS can freeze the terminal when tapes run back-to-back.
    # Reset terminal state and pause between recordings.
    reset 2>/dev/null
    sleep 1
done

if [[ ${#failed[@]} -gt 0 ]]; then
    echo "Done with failures. GIFs written to assets/images/"
    echo "Failed tapes: ${failed[*]}"
    exit 1
fi

echo "Done. GIFs written to assets/images/"
