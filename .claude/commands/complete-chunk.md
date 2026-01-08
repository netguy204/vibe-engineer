Add code references to the chunk represented by $ARGUMENTS and move both the PLAN.md and the GOAL.md to the ACTIVE state.

Start by identifying where in the code the goal is implemented. The PLAN.md file
in the chunk directory can help guide your search and git diff may provide clues
but may be more or less than the true scope of the code involved in the change.
Take note of the file names and the line ranges for semantically meaningful
(with respect to the GOAL.md) chunks of code and 