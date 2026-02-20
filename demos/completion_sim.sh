#!/bin/bash
# Simulates the --where tab completion experience for the demo GIF.
# Run via: bash demos/completion_sim.sh
source "$(dirname "$0")/lib.sh"

CMD="csvplot bar --file data/titanic.csv --column Embarked --where"

# Stage 1: type command with flag completions + column discovery, then show --where completions
printf '%s' "$PROMPT"
simulate_type "csvplot bar "
simulate_tab "--fi" "--file"
simulate_type " "
simulate_tab "data/ti" "data/titanic.csv"
simulate_type " "
simulate_tab "--col" "--column"
simulate_type " "
# Discovery: show all columns
sleep 1
echo ""
echo "Age          Cabin        Embarked     Fare         Name         Parch"
echo "PassengerId  Pclass       Sex          SibSp        Survived     Ticket"
printf '%s' "$PROMPT"
printf '%s' "csvplot bar --file data/titanic.csv --column "
sleep 2
simulate_type "Embarked"
simulate_type " "
simulate_tab "--wh" "--where"
simulate_type " "
# Discovery: show --where column= completions
sleep 1
echo ""
echo "Age=         Embarked=    Name=        PassengerId= Sex=         Survived="
echo "Cabin=       Fare=        Parch=       Pclass=      SibSp=       Ticket="
printf '%s' "$PROMPT"
printf '%s' "$CMD "
sleep 3

# Stage 2: type Sex=, "hit tab", show value completions
simulate_type "Sex="
sleep 1
echo ""
echo "female  male"
printf '%s' "$PROMPT"
printf '%s' "$CMD Sex="
sleep 3

# Stage 3: complete and run the actual command
simulate_type "female "
simulate_tab "--la" "--labels"
sleep 0.5
echo ""
$CMD Sex=female --labels
sleep 2
