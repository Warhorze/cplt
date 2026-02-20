#!/bin/bash
# Simulates typing the summarise demo command.
source "$(dirname "$0")/lib.sh"

printf '%s' "$PROMPT"
simulate_type "csvplot summarise "
simulate_tab "--fi" "--file"
simulate_type " "
simulate_tab "data/ti" "data/titanic.csv"
sleep 0.5
echo ""
csvplot summarise --file data/titanic.csv
sleep 2
