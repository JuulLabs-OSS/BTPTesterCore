"""This script allows to automatically construct CLI command that launches
Defensics with desired parameters. All parameters must be set to some value,
although initial values are the same as defaults. Some settings that are in
Test Suites are read-only, thus omitted"""

# Path to monitor boot.jar file
monitor_path = '/path/to/monitor/boot.jar'

# Test run settings
# ----------------------------------------------------------------------------------------------------------------------
btmon_logs_name = 'btmon-logs'

# Selection mode of test cases to run, allowed values are:
# - balanced
# - random
# - trim
# - first-and-last
selection_mode = 'trim'
# What percentage of test cases should be left to execute; this is used only
# for 'trim' selection mode
trim_percent = 1

# Should debug information should be included?
debug_info = True
# Should logs be saved to file?
capture_output = True

# Suite settings
# ----------------------------------------------------------------------------------------------------------------------
# SUITE_TYPE specifies what tests suite is used, without being version specific. Currently supported values are:
# 'btle-ad'
# 'btle-attc'
# 'btle-att'
# 'btle-hogp'
# 'btle-smpc'
suite_type = 'btle-smpc'

# Path to suite to run. It should be already installed.
suite_path = '/path/to/installed/suite/suite-name.jar'

# generate folder name based on chosen suite; can be swapped with any string
# if custom folder name should be used
folder_name = suite_type + '/'
results_path = '/path/to/results/folder/results/'

# Code for saved results of executed run. In '' user can put special characters that are listed in defensics help
# (e. g. # for number or letters for date. Not all suites support this formatting
test_code = '\'###\'-logs'

# commands to run in instrumentation-external
before_run = 'http://localhost:8000/before-run'
before_case = 'http://localhost:8000/before-case'
as_instrumentation = 'http://localhost:8000/as-instrumentation'
after_each = 'http://localhost:8000/after-case'
instrument_fail = 'http://localhost:8000/instrument-fail'
# after run should be modified in after-run.py

# Indices determining which tests are run can be in following format:
# - single integer
# - range of integers in form of list [start, end, interval]. If interval is optional with default value of 1
# - test case hash with 0x prefix (e.g. '0x9e9151ba1966f321')
# - Group name, for example 'UDP.request'
# - Wildcard * to match multiple groups, e.g. '*.valid' or 'UDP.*.element'.
# - Multiple index field entries are separated by commas, e.g. '0,10,20'
# This setting overrides selection_mode and should be left blank ('') to be omitted
test_indices = 1


# Settings of specific test suites
# ----------------------------------------------------------------------------------------------------------------------
# 1. Bluetooth-LE-Advertising-Data
#  Minimum advertising interval in milliseconds to use when sending the advertising data.
#  Allowed range is 20ms - 10000ms.
min_adv_intrvl_adv = 100
# Maximum advertising interval in milliseconds to use when sending advertising data. Allowed range is 20ms - 10000ms.
# The maximum interval must be equal or greater than the minimum interval.
max_adv_intrvl_adv = 200

# 2. Bluetooth-LE-ATT-Client
local_name_att = 'synopsys'
# If ACL link should be open between test cases choose --keep-link and --no-keep-link otherwise
keep_link_att = False
# How long to wait for input after establishing link in milliseconds
first_input_timeout = 5000
# How long to wait after test suit's last output before disconnecting in milliseconds
delay_before_disconnect = 0
# I/O capabilities - allowed values:
# - keyboard-only
# - display-only
# - display-and-keyboard
# - no-input-no-output
# - display-yes-no
io_capability_att = 'display-only'
passkey_att = '000000'
#  Minimum advertising interval in milliseconds to use when sending the advertising data.
#  Allowed range is 20ms - 10000ms.
min_adv_intrvl_att = 160
# Maximum advertising interval in milliseconds to use when sending advertising data. Allowed range is 20ms - 10000ms.
# The maximum interval must be equal or greater than the minimum interval.
max_adv_intrvl_att = 320
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
read_handle = '0x0003'
write_handle = '0x0005'

# 3 .Bluetooth-LE-ATT-Server
# MAC address of IUT
host_addr = 'e5:1b:60:02:a0:13'
addr_type = 'Random'
local_name_att_sr = 'synopsys'
# follow_rpa determines tester pairs with IUT, aquires IRK and resolves RPA.
follow_rpa = True
keep_link_att_sr = True
# Mark supervision timeouts as failures?
supervision_timeout_failure = True
# Enabling ATT server allows handling ATT requests by suite. By default it's disabled.
enable_att_sr = False
# Pair devices before test cases?
pair_devices = False
# Passkey to use when pairing, if pair_devices is False, this field isn't used.
passkey_att_sr = ''

# 4 .Bluetooth-LE-HOGP-Host
local_name_hogp = 'synopsys'
io_capability_hogp = 'no-input-no-output'
# Require Man-in-te-middle protection?
require_mitm = False
# Require bonding protection?
require_bonding = False

# 5. Bluetooth-LE-SMP-Client
local_name_smp = 'synopsys'
# Should ACL link be open between test cases?
keep_link_smp = False
# Enabling internal ATT server - if enabled, ATT requests will be responded to and ignored otherwise.
enable_att_sr_smp = True
# UUID to advertise when in connectable mode, should be in hexadecimal format.
uuid = '0x180a'
# Request bonding - enables exchanged keys storing.
bonding = True
passkey_smp = '000000'

# 6. CoAP-Server
# mandatory target nad host port setting; must contain "coap" URI scheme
coap_host_and_port = 'coap://127.0.0.1:5683'
# source port for sending
coap_sending_port = 52000
# Reuse TCP connection for multiple test cases? (current implementation of server requires True)
reuse_tcp = True
