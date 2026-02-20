#!/bin/bash
# Simulates typing the bar chart demo command.
source "$(dirname "$0")/lib.sh"

printf '%s' "$PROMPT"
simulate_type "csvplot bar "
simulate_tab "--fi" "--file"
simulate_type " "
simulate_tab "data/ti" "data/titanic.csv"
simulate_type " "
simulate_tab "--col" "--column"
simulate_type " "
# Discovery: show all columns, user picks Embarked
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
simulate_type " Sex=female "
simulate_tab "--la" "--labels"
sleep 0.5
echo ""
csvplot bar --file data/titanic.csv --column Embarked --where Sex=female --labels
sleep 2
