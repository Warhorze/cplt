#!/bin/bash
# Simulates typing the timeline demo command.
source "$(dirname "$0")/lib.sh"

# Show subcommand completion + help
printf '%s' "$PROMPT"
simulate_type "cplt "
simulate_tab "ti" "timeline"
simulate_type " --help"
echo ""
cplt timeline --help
sleep 2

# Clear and build the actual command
printf '%s' "$PROMPT"
simulate_type "cplt "
simulate_tab "ti" "timeline"
simulate_type " "
simulate_tab "--fi" "--file"
simulate_type " "
simulate_tab "da" "data/"
simulate_tab "pr" "projects.csv"
simulate_type " "
simulate_tab "--x" "--x"
simulate_type " "
# Discovery: show date columns (timeline --x only shows dates)
sleep 1
echo ""
echo "start_date  end_date"
printf '%s' "$PROMPT"
printf '%s' "cplt timeline --file data/projects.csv --x "
sleep 2
simulate_type "start_date"
simulate_type " --x "
simulate_tab "end" "end_date"
simulate_type " "
simulate_tab "--y" "--y"
simulate_type " "
# Discovery: show all columns for --y
sleep 1
echo ""
echo "end_date    project     start_date  status      team"
printf '%s' "$PROMPT"
printf '%s' "cplt timeline --file data/projects.csv --x start_date --x end_date --y "
sleep 2
simulate_type "project"
simulate_type " "
simulate_tab "--co" "--color"
simulate_type " "
simulate_tab "sta" "status"
simulate_type " --vline 2026-02-20 --label today"
sleep 0.5
echo ""
cplt timeline --file data/projects.csv --x start_date --x end_date --y project --color status --vline 2026-02-20 --label today
sleep 3
