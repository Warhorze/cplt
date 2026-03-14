#!/bin/bash
# Simulates typing the bar chart demo command.
source "$(dirname "$0")/lib.sh"

# Show subcommand completion + help
printf '%s' "$PROMPT"
simulate_type "cplt "
simulate_tab "ba" "bar"
simulate_type " --help"
echo ""
cplt bar --help
sleep 2

# Clear and build the actual command
printf '%s' "$PROMPT"
simulate_type "cplt "
simulate_tab "ba" "bar"
simulate_type " "
simulate_tab "--fi" "--file"
simulate_type " "
simulate_tab "da" "data/"
simulate_tab "ti" "titanic.csv"
simulate_type " "
simulate_tab "--col" "--column"
simulate_type " "
# Discovery: show all columns, user picks Embarked
sleep 1
echo ""
echo "Age          Cabin        Embarked     Fare         Name         Parch"
echo "PassengerId  Pclass       Sex          SibSp        Survived     Ticket"
printf '%s' "$PROMPT"
printf '%s' "cplt bar --file data/titanic.csv --column "
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
printf '%s' "cplt bar --file data/titanic.csv --column Embarked --where "
sleep 2
simulate_type "Sex="
# Discovery: show value completions
sleep 1
echo ""
echo "female  male"
printf '%s' "$PROMPT"
printf '%s' "cplt bar --file data/titanic.csv --column Embarked --where Sex="
sleep 2
simulate_type "female"
simulate_type " "
simulate_tab "--la" "--labels"
sleep 0.5
echo ""
cplt bar --file data/titanic.csv --column Embarked --where Sex=female --labels
sleep 3
