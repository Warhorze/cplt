#!/bin/bash
# Shared helpers for demo simulation scripts.

# Ensure cplt is available (add venv to PATH if present).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -d "$REPO_ROOT/.venv/bin" ]]; then
    export PATH="$REPO_ROOT/.venv/bin:$PATH"
fi

PROMPT="$ "

simulate_type() {
    local text="$1"
    for (( i=0; i<${#text}; i++ )); do
        printf '%s' "${text:$i:1}"
        sleep 0.04
    done
}

# Simulate tab-completing a flag or value.
# Usage: simulate_tab "--fi" "--file"
# Types the prefix char-by-char, pauses, then instantly prints the rest.
simulate_tab() {
    local prefix="$1"
    local full="$2"
    simulate_type "$prefix"
    sleep 0.5
    printf '%s' "${full:${#prefix}}"
    sleep 0.5
}
