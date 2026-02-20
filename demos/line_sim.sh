#!/bin/bash
# Simulates typing the line chart demo command.
source "$(dirname "$0")/lib.sh"

printf '%s' "$PROMPT"
simulate_type "csvplot line "
simulate_tab "--fi" "--file"
simulate_type " "
simulate_tab "data/te" "data/temperatures.csv"
simulate_type " "
simulate_tab "--x" "--x"
simulate_type " "
# Discovery: show all columns (only 2), user picks Date
sleep 1
echo ""
echo "Date  Temp"
printf '%s' "$PROMPT"
printf '%s' "csvplot line --file data/temperatures.csv --x "
sleep 2
simulate_type "Date"
simulate_type " "
simulate_tab "--y" "--y"
simulate_type " "
# User already saw the columns, just tab-complete
simulate_tab "Te" "Temp"
simulate_type " --head 40 "
simulate_tab "--ti" "--title"
simulate_type " 'Melbourne Min Temp'"
sleep 0.5
echo ""
csvplot line --file data/temperatures.csv --x Date --y Temp --head 40 --title 'Melbourne Min Temp'
sleep 2
