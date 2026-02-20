#!/bin/bash
# Simulates typing the bubble matrix demo command.
source "$(dirname "$0")/lib.sh"

# Show subcommand completion + help
printf '%s' "$PROMPT"
simulate_type "csvplot "
simulate_tab "bu" "bubble"
simulate_type " --help"
echo ""
csvplot bubble --help
sleep 2

# Clear and build the actual command
printf '%s' "$PROMPT"
simulate_type "csvplot "
simulate_tab "bu" "bubble"
simulate_type " "
simulate_tab "--fi" "--file"
simulate_type " "
simulate_tab "da" "data/"
simulate_tab "ti" "titanic.csv"
simulate_type " "
simulate_tab "--col" "--cols"
simulate_type " "
# Discovery: show all columns, user picks Cabin
sleep 1
echo ""
echo "Age          Cabin        Embarked     Fare         Name         Parch"
echo "PassengerId  Pclass       Sex          SibSp        Survived     Ticket"
printf '%s' "$PROMPT"
printf '%s' "csvplot bubble --file data/titanic.csv --cols "
sleep 2
simulate_type "Cabin"
# User already saw columns, tab-complete the rest
simulate_type " --cols "
simulate_tab "Ag" "Age"
simulate_type " --cols "
simulate_tab "Emb" "Embarked"
simulate_type " "
simulate_tab "--y" "--y"
simulate_type " "
simulate_tab "Na" "Name"
simulate_type " --head 12 "
simulate_tab "--co" "--color"
simulate_type " "
simulate_tab "Se" "Sex"
sleep 0.5
echo ""
csvplot bubble --file data/titanic.csv --cols Cabin --cols Age --cols Embarked --y Name --head 12 --color Sex
sleep 3
