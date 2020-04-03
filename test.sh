#!/bin/bash
# check if test process already exists and if it does, terminate it.
# This is used to end existing communication with devices and assure,
# that tests are run fresh and thus replicable

pkill -f "btptester main.py" # this sends SIGKILL
exec -a btptester python3 main.py &>test.log | at now + 0 minute
exit 0
