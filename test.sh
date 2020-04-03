#!/bin/bash
python3 main.py &>test.log | at now + 1 minute
exit 0