# Testing Mynewt with Synopsys Defensics
## Defensics setup
Installer is run from shell script. Add execution permission and run it:

```Shell
$ cd installer-###-###/installer
$ chmod +x defensics-installer-20XX.YY.sh
$ ./defensics-installer-20XX.XX.sh
```

and follow instructions. After installation run Defensics:

```Shell
$ java -Xmx768M -jar /full_installation_path/Defensics/monitor/boot.jar
```

Please note that some suites (e.g. BLE tests) might require running Defensics as root.

To add test suite click `Open suite browser to load suites` button, then `Install suite`
Follow directory with suite installers and double-click on a desired one. By default, only .jar
files are visible, but .zip files are also supported. After installation double click
suite on list or click `Load`
## IUT setup
### General setup
For most suites BTP Tester uses Mynewt `bttester` app, living in Mynewt Nimble repository.
Basic configuration of app might be modified using `syscfg.yml` file in target directory.
For most uses default configuration is sufficient, although redirecting IUT logs from UART
to RTT might be useful. To do it, add:
```yaml
syscfg.vals:
    CONSOLE_RTT: 1
    CONSOLE_UART: 0
```
This kind of data might be read using [rtt2pty](https://github.com/codecoup/tools-rtt2pty) as a bridge,
and then minicom-like tool to read from PTY. What levels of logs have to be collected is set
using:
```yaml
    BLE_HS_LOG_LVL: 0-4 # this is BT host log level
    LOG_LEVEL: 0-4 # general log level
    OC_LOG_LVL: 0-4 # OC log level, this includes CoAP logs
```
where 1-4 are valid values to be used in these settings:
- 0 - DEBUG
- 1 - INFO
- 2 - WARN
- 3 - ERROR
- 4 - CRITICAL

In config one can also enable BT monitor:
```yaml
    BLE_MONITOR_RTT: 1
```

To read its logs use btmon tool (part of [bluez](http://www.bluez.org/)) like this (assuming
nrf52 board is used):
```shell
$ btmon -J nrf52
```
To save logs run this command with `-w` flag and pass filename as argument. This file is in btsnoop
format and can be later read using:
```shell
$ btmon -r filename
```

### IUT setup for CoAP testing
Testing CoAP requires using `bleprph_oic` app living in Mynewt Core repository.  It can be configured
in similar manner as bttester, but because reading IUT logs, crash detection and BT monitor log saving
is automated, config must take that into consideration:
- BT monitor and logs reading both use RTT
- crash detection uses [Newtmgr](https://github.com/apache/mynewt-newtmgr); this requires to use serial
  transport and excludes using it along logs reading
  
To use crash detection function we must configure app this way:
```yaml
    OS_COREDUMP: 1 # attempt to write coredump at OS crash
    IMGMGR_COREDUMP: 1 # enable coredump management commands
    IMGMGR_CLI: 1 # enables image command
    SHELL_TASK: 1 # initiate shell task for Newtmgr to use
    OC_TRANSPORT_SERIAL: 1 # transport for Newtmgr
    OC_TRANSPORT_BLE: 1 # transport for CoAP
```
Corefile download speed depends on UART tx buffer size. Default value is 32. Although this works fine,
download is pretty slow. To speed it up increase this value:
```yaml
    CONSOLE_UART_TX_BUF_SIZE: 128
```
Value of 128 was tested on nrf52840_dk board. This value can be fine-tuned; however, larger values
might result in failed transmission - sending might abort, and Newtmgr will return `NMP timeout`
error.

## Running tests from Defensics GUI
### Running BLE tests
#### Server setup
NOTE: this part assumes that no other BT dongles are plugged in besides PTS dongle and all commands
are run from BTPTester directory.

Before any test is executed from Defensics, instrumentation server must be launched. To do it, run
in terminal:
```shell
$ python3 defensics/main.py
```
This provides sane defaults for the server; to see runtime parameters call:

```shell
$ python3 defensics/main.py -h
```
You can see here parameter called `INDEX`. This value has to be checked to be valid. It tells the
server which hci to use when IUT has to interact with PTS dongle. To start with, make sure all
connected devices are detected by system:
```shell
$  rfkill list
0: tpacpi_bluetooth_sw: Bluetooth
	Soft blocked: no
	Hard blocked: no
1: phy0: Wireless LAN
	Soft blocked: no
	Hard blocked: no
2: hci0: Bluetooth
	Soft blocked: no
	Hard blocked: no
3: hci1: Bluetooth
	Soft blocked: no
	Hard blocked: no
```
here, we can see 2 hci devices, and all of them aren't blocked. One of them is a built-in laptop BT
radio, while the other one is PTS dongle. If devices are locked, try restarting BT service:
```shell
# sudo service bluetooth restart
```
Assuming the hci devices aren't blocked, check which one is PTS dongle:
```shell
$ hciconfig -a
hci1:	Type: Primary  Bus: USB
	BD Address: 00:1B:DC:F2:1C:3F  ACL MTU: 310:10  SCO MTU: 64:8
	DOWN 
	RX bytes:615 acl:0 sco:0 events:34 errors:0
	TX bytes:386 acl:0 sco:0 commands:33 errors:0
	Features: 0xff 0xff 0x8f 0x7e 0xd8 0x1f 0x5b 0x87
	Packet type: DM1 DM3 DM5 DH1 DH3 DH5 HV1 HV2 HV3 
	Link policy: RSWITCH HOLD SNIFF PARK 
	Link mode: SLAVE ACCEPT 

hci2:	Type: Primary  Bus: USB
	BD Address: 00:1B:DC:F2:1C:36  ACL MTU: 310:10  SCO MTU: 64:8
	UP RUNNING PSCAN ISCAN 
	RX bytes:1826 acl:0 sco:0 events:81 errors:0
	TX bytes:1134 acl:0 sco:0 commands:80 errors:0
	Features: 0xff 0xff 0x8f 0x7e 0xd8 0x1f 0x5b 0x87
	Packet type: DM1 DM3 DM5 DH1 DH3 DH5 HV1 HV2 HV3 
	Link policy: RSWITCH HOLD SNIFF PARK 
	Link mode: SLAVE ACCEPT 
	Name: 'user #3'
	Class: 0x1c010c
	Service Classes: Rendering, Capturing, Object Transfer
	Device Class: Computer, Laptop
	HCI Version: 4.2 (0x8)  Revision: 0x30e8
	LMP Version: 4.2 (0x8)  Subversion: 0x30e8
	Manufacturer: Cambridge Silicon Radio (10)

hci0:	Type: Primary  Bus: USB
	BD Address: D8:F2:CA:54:FD:2A  ACL MTU: 1021:4  SCO MTU: 96:6
	UP RUNNING PSCAN 
	RX bytes:19143 acl:0 sco:0 events:2664 errors:0
	TX bytes:599391 acl:0 sco:0 commands:2560 errors:0
	Features: 0xff 0xfe 0x0f 0xfe 0xdb 0xff 0x7b 0x87
	Packet type: DM1 DM3 DM5 DH1 DH3 DH5 HV1 HV2 HV3 
	Link policy: RSWITCH HOLD SNIFF 
	Link mode: SLAVE ACCEPT 
	Name: 'user'
	Class: 0x1c010c
	Service Classes: Rendering, Capturing, Object Transfer
	Device Class: Computer, Laptop
	HCI Version: 4.2 (0x8)  Revision: 0x100
	LMP Version: 4.2 (0x8)  Subversion: 0x100
	Manufacturer: Intel Corp. (2)
```
Here we can see three results: 
- hci0 device is manufactured by Intel - this might vary, but results like this is built-in BT
  device
- hci1 - this might be PTS dongle, but requires checking
- hci2 - this is PTS dongle - manufacturer is Cambridge Silicon Radio

Defensics will choose first hci device that is PTS dongle- thus, we must check what hci1 is:
```shell
$ sudo hciconfig hci1 up
$ hciconfig -a
...
hci1:	Type: Primary  Bus: USB
	BD Address: 00:1B:DC:F2:1C:36  ACL MTU: 310:10  SCO MTU: 64:8
	UP RUNNING PSCAN ISCAN 
	RX bytes:1272 acl:0 sco:0 events:75 errors:0
	TX bytes:1116 acl:0 sco:0 commands:74 errors:0
	Features: 0xff 0xff 0x8f 0x7e 0xd8 0x1f 0x5b 0x87
	Packet type: DM1 DM3 DM5 DH1 DH3 DH5 HV1 HV2 HV3 
	Link policy: RSWITCH HOLD SNIFF PARK 
	Link mode: SLAVE ACCEPT 
	Name: 'user #2'
	Class: 0x1c010c
	Service Classes: Rendering, Capturing, Object Transfer
	Device Class: Computer, Laptop
	HCI Version: 4.2 (0x8)  Revision: 0x30e8
	LMP Version: 4.2 (0x8)  Subversion: 0x30e8
	Manufacturer: Cambridge Silicon Radio (10)

...
```
We can see that it's another Cambridge Silicon Radio. Because this is hci1 device - lower than hci2 -
this is what Defensics will use. We need to pass as argument for the server:
```shell
$ python3 defensics/main.py -i 1
```
Next, we can configure Defensics.
#### Defensics GUI
In [Defensics setup](#defensics-setup) we have loaded a suite. On the left we have bar organised to
steps user is expected to take when running tests:

![Alt text](test_steps.png?raw=true)

Let's walk through these tabs:

1. Basic - here we set up parameters of communication between Defensics and IUT. Contents of this tab
   vary from suite to suite. Usually provided values are sane.
2. Interoperability - each test group has valid case; interoperability allows us to check if these
   valid cases indeed pass, or are unsupported. It's good to run this before every test run, because
   it allows us to check if everything is set up properly. Before running these tests, however, Advanced
   and Instrumentation has to be setup
3. Advanced - here we can accommodate data collection and run control. Again, defaults are mostly sane,
   but for certain suites (e.g. CoAP) require adjusting
4. Instrumentation allows us to interact with IUT and check it's state  by running scripts and commands.
   BTPTester uses it to execute test cases and manage IUT. In sub-tab `External` are 6 fields that must be
   filled as follows (BTPTesterCore_path is path to this repo, e.g. /home/user/BTPTesterCore):
   - `python3 BTPTesterCore_path/defensics/instrumentation_client.py http://localhost:8000/before-run`
   - `python3 BTPTesterCore_path/defensics/instrumentation_client.py http://localhost:8000/before-case`
   - `python3 BTPTesterCore_path/defensics/instrumentation_client.py http://localhost:8000/as-instrumentation`
   - `python3 BTPTesterCore_path/defensics/instrumentation_client.py http://localhost:8000/after-case`
   - `python3 BTPTesterCore_path/defensics/instrumentation_client.py http://localhost:8000/instrument-fail`
   - `python3 BTPTesterCore_path/defensics/instrumentation_client.py http://localhost:8000/after-run`
   
   In `Instrumentation` sub-tab `Valid case instumentation` shall be disabled - this is verified by us by
   checking if IUT is responding to commands after test.
5. Test cases - here test to run can be selected. Big banner allows to choose rule of picking tests (e.g.
   first and last of each group or 1%). In tree these picks might be narrowed and in table below individual
   tests can be selected
6. Test run - run selected cases
7. Results - see statistics (table summary of pass/failed cases) and logs from test execution (from Defensics
   point of view)
8. Remediation - create package with detected bugs
### Running CoAP tests
CoAP testing part of BTPTester was designed to test CoAP over BLE using TCP protocol. Because CoAP suite
is not a part of BLE test suite group, Defensics provides general communication sending its data to port.
Thus, BTPTester provides the proxy between Defensics and IUT. Architecture of this system can be illustrated
as follows:

![Alt text](CoAP_testing_system.png?raw=true)

Because Defensics isn't speaking directly to IUT, additional configuration is required:
1. Basic:
   - Basic:
     - Target URI nad Port: `coap://127.0.0.1:5683`
   - Connection Settings:
     - Source Port for sending: 52000
   - TCP/Websocket coap setup:
     - Reuse connection: Yes
     - Enable TLS: disabled
2. Interoperability: choose CoAP-TCP from dropdown menu:
   
   ![Alt text](coap_dropdown.png?raw=true)

3. Advanced
   - Run control - values here might be fine-tuned but these values are sane and were tested:
      - Timeout of received messages (ms): 10000
      - Output timeout (ms): -1
      - Loop test cases: depends on user
      - Test case delay (ms): 1000
      - Valid case instrumentation delay (ms): 30000
4. Instrumentation
   - Instrumentation
      - Valid case instrumentation: no. This is verified using NewtMgr
      - External: same settings as in [Defensics GUI](####Defensics-GUI)

BTPTester must be configured by editing `coap_config.py`; here, you can enable:
- crash detection - this requires also setting sudo password, because Newtmgr has to be run as sudo
  to access serial port
- btmon log saving
- IUT logs saving

One obligatory value here is `reset_cmd` - shell command that restarts IUT. Restarts happen automatically
after avery failed case.
Before running tests proxy must be launched:
```shell
$ python3 defensics/coap_main.py
```
## Running tests using Defensics in CLI mode
Defensics might be also run without GUI. BTPTester provides a launcher that automatically runs both Defensics
and required BTPTester modules. Settings of this launcher can be modified in `defensics_config.py`, although
default settings are good starting point. Launcher can be used by executing `defensics_launcher.py`:
```shell
$ python3 defensics/defensics_launcher.py
```
Using launcher with CoAP suite requires setting `coap_config.py` too, as described in 
[Running CoAP tests](###running-coap-tests)

## Interpreting the results
Defensics results can be browsed in `Results` tab. Tree on the left shows all results saved in result directory.
These are executed runs; their markings are:

1. Red - Run contains some failed cases
2. Green - All tests in run passed
3. Gray - Test run result is inconclusive
4. Traffic lights - Interoperability run

Clicking on a test run will open its details in the central panel. In `Statistics` view you can see tabular comparison
of executed tests which are also color-coded. Interpretation of these results depends on a suite and test.
As Defensics is fuzz-testing platform, the tests don't expect IUT to perform correct actions; this is only
expected for Interoperability tests. What Defensics tests is if the IUT is still working properly after
receiving malformed data. Thus results say:
1. White - test passed. It means that IUT responded with proper action (for Interoperability) or is still working
    after test.
2. Yellow - Inconclusive result (also includes case when user stopped testcase)
3. Red - Test failed; this doesn't mean necessarily that IUT crashed or failed;
    what it means is that Defensics haven't received response (if it was expecting receiving one), or more likely,
    that instrumentation failed. Failing instrumentation may be caused by unresponsive IUT (maybe because of crash
    or deadlock) or inability to execute instrumentation. This may be caused simply because of IUT disconnecting
    from the server or Defensics. This case is false-positive: malformed data may cause IUT to abandon connection
    as self-defense mechanism.
   