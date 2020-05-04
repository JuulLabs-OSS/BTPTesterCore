#!/bin/bash
# Variables that user is encouraged to change are in capital letters.
# Small letters denote helper variables and should not be changed.
# All parameters must be set to some value, although initial values are the same as defaults.
# Some settings that are in Test Suites are read-only, thus omitted

# Path to monitor boot.jar file
MONITOR_PATH="/path/to/monitor/boot.jar"
# Test run settings
# ----------------------------------------------------------------------------------------------------------------------
# Selection mode of test cases to run, allowed values are:
# - balanced
# - random
# - trim
# - first-and-last
SELECTION_MODE="trim"
selection_cmd="--selection-mode $SELECTION_MODE"
if [ "$SELECTION_MODE" = "trim" ] ; then
  # What percentage of test cases should be left to execute
  TRIM_PERCENT="1"
  trim_cmd="--trim-percent $TRIM_PERCENT"
fi
# If full debug information should be included, keep this variable, put it in comment otherwise
VERBOSE="--verbose"
# Setting CAPTURE_OUTPUT to 1 saves console logs to file, otherwise doesn't
CAPTURE_OUTPUT=1

# Suite settings
# ----------------------------------------------------------------------------------------------------------------------
# SUITE_TYPE specifies what tests suite is used, without beeing version specific. Currently supported values are:
# "btle-ad"
# "btle-attc"
# "btle-att"
# "btle-hogp"
# "btle-smpc"

SUITE_TYPE = "btle-ad"
# Path to suite to run. It should be already installed. Few paths are included in this comment for ease of use
SUITE="/path/to/installed/suite/"

# generate folder name based on chosen suite; can be swapped with any string
extract_name_helper=${SUITE#*testtool/}
suite_name=${extract_name_helper%.jar*}
FOLDER_NAME=$suite_name"/"
RESULTS_PATH="/path/to/results/folder/results/"
# Code for saved results of executed run. In '' user can put special characters that are listed in defensics help
# (e. g. # for number or letters for date. Not all suites support this formatting
TEST_CODE="'###'-logs"

# commands to run in instrumentation-external
BEFORE_RUN="python3 $PWD/instrumentation_client.py http://localhost:8000/before-run"
BEFORE_CASE="python3 $PWD/instrumentation_client.py http://localhost:8000/before-case"
AS_INSTRUMENTATION="python3 $PWD/instrumentation_client.py http://localhost:8000/as-instrumentation"
AFTER_EACH="python3 $PWD/instrumentation_client.py http://localhost:8000/after-case"
INSTRUMENT_FAIL="python3 $PWD/instrumentation_client.py http://localhost:8000/instrument-fail"
# this has to  be single command with no params
AFTER_RUN="$PWD/after-run.py"

# indicies can be in following format:
# - single integer
# - test case hash with 0x prefix (e.g. 0x9e9151ba1966f321)
# - Group name, for example UDP.request
# - Wildcard * to match multiple groups, e.g. "*.valid" or "UDP.*.element".
# - Multiple index field entries are separated by commas, e.g. "0,10,20". This can be also generated using get_every_nth_case()
#   method with arguments: starting index, maximum index, step between test cases
# This setting overrides SELECTION MODE
TEST_INDICIES="1-5"
function get_every_nth_case {
  local start=$1
  local end=$2
  local step=$3
  local i=1
  TEST_INDICIES="$start"
  i=$(( $i+$step ))
  while [ $i -le $end ]
  do
    TEST_INDICIES+=",$i"
    i=$(( $i+$step ))
  done
}
# if get_every_nth_case not used, comment this line; else, fill with desired values
#get_every_nth_case 1 2000 10
if [ "$TEST_INDICIES" != "" ] ; then
  selection_cmd=""
  trim_cmd=""
  test_indicies_cmd="--index $TEST_INDICIES"
else
  test_indicies_cmd=""
fi

# Settings of specific test suites
# ----------------------------------------------------------------------------------------------------------------------
# 1. Bluetooth-LE-Advertising-Data
#  Minimum advertising interval in milliseconds to use when sending the advertising data. Allowed range is 20ms - 10000ms.
MIN_ADV_INTRVL_ADV=100
# Maximum advertising interval in milliseconds to use when sending advertising data. Allowed range is 20ms - 10000ms.
# The maximum interval must be equal or greater than the minimum interval.
MAX_ADV_INTRVL_ADV=200
adv_cmds=(
  "--min-adv-interval $MIN_ADV_INTRVL_ADV"
  "--max-adv-interval $MAX_ADV_INTRVL_ADV"
)
composed_adv_cmd=$(printf " %s" "${adv_cmds[@]}")
composed_adv_cmd=${composed_adv_cmd:1}

# 2. Bluetooth-LE-ATT-Client
LOCAL_NAME_ATT="synopsys"
# If ACL link should be open between test cases choose --keep-link and --no-keep-link otherwise
KEEP_LINK_ATT="--no-keep-link"
# How long to wait for input after establishing link in milliseconds
FIRST_INPUT_TIMEOUT="5000"
# How long to wait after test suit's last output before disconnecting in milliseconds
DELAY_BEFORE_DISCONNECT="0"
# I/O capabilities - allowed values:
# - keyboard-only
# - display-only
# - display-and-keyboard
# - no-input-no-output
# - display-yes-no
IO_CAPABILITY_ATT="display-only"
PASSKEY_ATT="000000"
#  Minimum advertising interval in milliseconds to use when sending the advertising data. Allowed range is 20ms - 10000ms.
MIN_ADV_INTRVL_ATT=160
# Maximum advertising interval in milliseconds to use when sending advertising data. Allowed range is 20ms - 10000ms.
# The maximum interval must be equal or greater than the minimum interval.
MAX_ADV_INTRVL_ATT=320
# Handles for read/write cases. Allowed values for both are:
# 0x0003
# 0x0005
# 0x0008
# 0x000a
# 0x000c
# 0x000e
# 0x0010
# 0x0012
# 0x0015
READ_HANDLE="0x0003"
WRITE_HANDLE="0x0005"
att_cl_cmds=(
  "--local-name $LOCAL_NAME_ATT"
  "--first-input-timeout $FIRST_INPUT_TIMEOUT"
  "--delay-before-disconnect $DELAY_BEFORE_DISCONNECT"
  "--io-capability $IO_CAPABILITY_ATT"
  "--passkey $PASSKEY_ATT"
  "--min-adv-interval $MIN_ADV_INTRVL_ATT"
  "--max-adv-interval $MAX_ADV_INTRVL_ATT"
  "--read-handle $READ_HANDLE"
  "--write-handle $WRITE_HANDLE"
)
composed_att_cl_cmd=$(printf " %s" "${att_cl_cmds[@]}")
composed_att_cl_cmd=${composed_att_cl_cmd:1}

# 3 .Bluetooth-LE-ATT-Server
# MAC address of IUT
HOST_ADDR="e5:1b:60:02:a0:13"
ADDR_TYPE="Random"
LOCAL_NAME_ATT_SR="synopsys"
# Use --follow-resolvable to pair with IUT, acquire IRK and resolve RPA. If IRK doesn't exist error will be raised.
# Using --dont-follow-resolvable will result in not resolving RPA
FOLLOW_RPA="--follow-resolvable"
KEEP_LINK_ATT_SR="--keep-link"
# Mark supervision timeouts as failures using --supervision-timeout-failure or not using --no-supervision-timeout-failure
SUPERVISION_TIMEOUT_FAILURE="--supervision-timeout-failure"
# Enabling ATT server using --enable-att-server in suite allows handling ATT requests by suite.
# By default it's disabled (--disable-att-server)
ENABLE_ATT_SR="--disable-att-server"
# Pair devices before test cases using --enable-pairing, use --no-enable-pairing otherwise
PAIR_DEVICES="--no-enable-pairing"
# Passkey to use when pairing, if --no-enable-pairing is set, then this field can be empty
PASSKEY_ATT_SR=""
att_sr_cmds=(
  "--host $HOST_ADDR"
  "--addr-type $ADDR_TYPE"
  "--local-name $LOCAL_NAME_ATT_SR"
  $FOLLOW_RPA
  $SUPERVISION_TIMEOUT_FAILURE
  $ENABLE_ATT_SR
  $PAIR_DEVICES
)
if [ "$PASSKEY_ATT_SR" != "" ] ; then
  att_sr_cmds+=("--passkey $PASSKEY_ATT_SR")
fi
composed_att_sr_cmd=$(printf " %s" "${att_sr_cmds[@]}")
composed_att_sr_cmd=${composed_att_sr_cmd:1}

# 4 .Bluetooth-LE-HOGP-Host
LOCAL_NAME_HOGP="synopsys"
IO_CAPABILITY_HOGP="no-input-no-output"
# Require Man-in-te-middle protection using --require-mitm, --no-require-mitm otherwise
REQUIRE_MITM="--no-require-mitm"
# Require bonding protection using --require-bonding, --no-require-bonding otherwise
REQUIRE_BONDING="--no-require-bonding"
hogp_host_cmds=(
  "--local-name $LOCAL_NAME_HOGP"
  "--io-capability $IO_CAPABILITY_HOGP"
  $REQUIRE_MITM
  $REQUIRE_BONDING
)
composed_hogp_host_cmd=$(printf " %s" "${hogp_host_cmds[@]}")
composed_hogp_host_cmd=${composed_hogp_host_cmd:1}

# 5. Bluetooth-LE-SMP-Client
LOCAL_NAME_SMP="synopsys"
# If ACL link should be open between test cases choose --keep-link and --no-keep-link otherwise
KEEP_LINK_SMP="--no-keep-link"
# Enabling internal ATT server - if enabled, ATT requests will be responded to and ignored otherwise.
# Use --enable-att-server or --disable-att-server
ENABLE_ATT_SR_SMP="--enable-att-server"
# UUID to advertise when in connectable mode, should be in hexadecimal format
UUID="0x180a"
# Request bonding - enables exchanged keys storing. Value --bonding or --no-bonding
BONDING="--bonding"
PASSKEY_SMP="000000"
smp_cl_cmds=(
  "--local-name $LOCAL_NAME_SMP"
  $KEEP_LINK_SMP
  $ENABLE_ATT_SR_SMP
  "--uuid $UUID"
  $BONDING
  "--passkey $PASSKEY_SMP"
)
composed_smp_cl_cmd=$(printf " %s" "${smp_cl_cmds[@]}")
composed_smp_cl_cmd=${composed_smp_cl_cmd:1}

log_path=""
log_path=$RESULTS_PATH$FOLDER_NAME$TEST_CODE

cmds=(
  "java -jar $MONITOR_PATH"

  # [options]
  $selection_cmd
  $trim_cmd
  $VERBOSE
  "--exec-after-test-run $AFTER_RUN"
#  "--max-fails-limit 1"
  # [suite]
  "--suite $SUITE"
  # [suite options]
  "--log-dir $log_path"
  "--no-loop"
  "--exec-test-run $BEFORE_RUN"
  "--exec-pre-test-case $BEFORE_CASE"
  "--exec-instrument $AS_INSTRUMENTATION"
  "--exec-post-test-case $AFTER_EACH"
  "--exec-instrument-fail $INSTRUMENT_FAIL"
  "$test_indicies_cmd"
)

# construct command and run defensics
composed_cmd=$(printf " %s" "${cmds[@]}")
composed_cmd=${composed_cmd:1}
# append to command suite specific settings
if [ "$SUITE_TYPE" = "btle-ad" ] ; then
  complete_cmd=$composed_cmd" "$composed_adv_cmd
elif [ "$SUITE_TYPE" = "btle-attc" ] ; then
  complete_cmd=$composed_cmd" "$composed_att_cl_cmd
elif [ "$SUITE_TYPE" = "btle-att" ] ; then
  complete_cmd=$composed_cmd" "$composed_att_sr_cmd
elif [ "$SUITE_TYPE" = "btle-hogp" ] ; then
  complete_cmd=$composed_cmd" "$composed_hogp_host_cmd
elif [ "$SUITE_TYPE" = "btle-smpc" ] ; then
  complete_cmd=$composed_cmd" "$composed_smp_cl_cmd
# if other suite is used, no settings are added
else
  complete_cmd=$composed_cmd
fi

if [ $CAPTURE_OUTPUT = 1 ] ; then
  echo -e "Executed command:\n"$complete_cmd > run-info.log
  sudo bash -c "$complete_cmd" >> run-info.log
else
  echo -e "Executed command:\n"$complete_cmd
  sudo bash -c "$complete_cmd"
fi
exit 0
