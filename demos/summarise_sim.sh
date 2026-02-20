#!/bin/bash
# Simulates typing the summarise demo command.
source "$(dirname "$0")/lib.sh"

# Show subcommand completion + help
printf '%s' "$PROMPT"
simulate_type "csvplot "
simulate_tab "su" "summarise"
simulate_type " --help"
echo ""
csvplot summarise --help
sleep 2

# Clear and build the actual command
printf '%s' "$PROMPT"
simulate_type "csvplot "
simulate_tab "su" "summarise"
simulate_type " "
simulate_tab "--fi" "--file"
simulate_type " "
simulate_tab "da" "data/"
simulate_tab "ti" "titanic.csv"
sleep 0.5
echo ""
csvplot summarise --file data/titanic.csv
sleep 3
