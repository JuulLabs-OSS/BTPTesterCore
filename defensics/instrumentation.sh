#!/bin/bash
# How many instrumentation rounds have to fail before system is restarted and checked for crashes (10 is sane default)
inst_rounds_before_restart=10
# On wich port appears output from board running Mynewt
board_console_out="/dev/ttyACM0"
# newtmgr connection profile name
newtmgr_profile="coap"
logs_path="`( cd \"$MY_PATH\" && pwd )`"
btptestercore_path="path/to/BTPTesterCore"
if [ "$1" == "before-run" ]; then
  echo Running suite: $CODE_SUITE
  echo Platform version: $CODE_SUITE_PLATFORM_VERSION
  echo Monitor version: $CODE_MONITOR_VERSION
  mkdir -p "$btptestercore_path/results"
elif [ "$1" == "before-case" ]; then
  mkdir -p "$btptestercore_path/results/#$CODE_TEST_CASE"
  echo Test group: $CODE_TEST_GROUP
  echo Test hash: $CODE_TEST_HASH
  echo Test index: $CODE_TEST_CASE
  # Save HCI traces using btmon
  nohup btmon -J nrf52 -w $CODE_TEST_CASE.snoop 0<&- &>/dev/null &
  # Save output from board console
  nohup cat /dev/ttyACM0 0<&- &>$CODE_TEST_CASE.log &
# "As instrumentation" is omitted - Defensics determines test result on its own
elif [ "$1" == "after-each" ]; then
  # terminate btmon and output saving
  pkill -f "btmon -J nrf52 -w $CODE_TEST_CASE"
  pkill -f "cat $board_console_out"
  # make copy of all result files in BTPTesterCore folder (*.log and *.snoop only for failed cases)
  cp "$logs_path/$CODE_TEST_CASE.log" "$btptestercore_path/results/#$CODE_TEST_CASE"
  cp "$logs_path/$CODE_TEST_CASE.snoop" "$btptestercore_path/results/#$CODE_TEST_CASE"
  cp "$CODE_RESULT_DIR" "$btptestercore_path/results/" -r
elif [ "$1" == "fail" ]; then
  if [ $CODE_INST_ROUNDS -lt $inst_rounds_before_restart ]; then
    # terminate tcp server with proxy
    pkill -f "coap_main.py"
      # restart board
      if nrfjprog -r; then
        echo Board restarted
      # failed board restart implies bluez crash
      else
        echo Bluez is unresponsive
        service bluetooth restart
      fi
      # after restarts board can be checked for crash - corefile should be able to be downloaded
      # check if Mynewt has corefile to download)
      if newtmgr -c $newtmgr_profile image corelist | grep 'Corefile present' &> /dev/null; then
        newtmgr -c $newtmgr_profile image coredownload $CODE_TEST_CASE_coredump
        # after download corefile might be removed from board
        newtmgr -c $newtmgr_profile image coreerase
      fi
  fi
  # restart tcp server
  nohup python3 $btptestercore_path/defensics/coap_main.py 0<&- &>/dev/null &
elif [ "$1" == "after-run" ]; then
  # Assure that result folder doesn't have root permissions
  chmod a+rw "$btptestercore_path/results/" -R
  pkill -f "coap_main.py"
fi
