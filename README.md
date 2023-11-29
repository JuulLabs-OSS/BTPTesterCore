# BTPTesterCore

End-to-end automated Bluetooth testing application. Uses 
[Bluetooth Testing Protocol](https://github.com/intel/auto-pts/blob/master/doc/btp_spec.txt) 
for communication. Currently supports Mynewt Nimble and Android systems.

This tool tests various features from GAP and GATT protocol, i.e.
 - advertising
 - scanning
 - connection
 - pairing
 - connection parameter update
 - GATT database discovery
 - GATT read/write/notify/indicate

Using this framework more testcases can be implemented to cover more 
Bluetooth Low Energy features.

`testcases/` directory contains files with the implementations of these
testcases.

#### Requirements (tested on Ubuntu 19.10)

- Python 3
- Ubuntu packages
  - python3-dev
  - libdbus-1-dev
  - libcairo2-dev
  - libgirepository1.0-dev
  - socat
  - adb (when testing with Android)
  - virtualenv (recommended)
  - at (optional for run scheduling)

- pip install -r requirements.txt

- nrfjprog (download `nRF Command Line Tools` from Nordic's website)

#### Testing with Mynewt Nimble

To test with Mynewt Nimble the Device Under Test should run 
[bttester](https://github.com/apache/mynewt-nimble/tree/master/apps/bttester) 
app from Apache Mynewt Nimble repository. It uses serial port to communicate with 
BTPTesterCore app running on a computer. Testing with Mynewt relies on 
`nrfjprog` CLI app for listing and resetting devices. That means only 
Nordic nRF5x devices are supported right now. Adding support for other 
devices and transports should be fairly simple so feel free to submit PRs.

**Configuration:**

To create a connection with a Mynewt device you need to specify it in the
arguments

Example: 
```
python3 main.py --use-mynewt
```

#### Testing with Android

To test with Android device you should use [BTPTesterAndroid](https://github.com/JuulLabs-OSS/BTPTesterAndroid)
 \- a dedicated Bluetooth testing app. It uses WebSocket technology to
communicate with the Core app. The Android app runs a WebSocket server
(which is a bit unusual, typically a mobile device is the client) and
BTPTesterCore runs a WebSocket client that connects to the Android 
app. When the connection is established, BTP packets can be sent
in both directions.

The tool supports using multiple Android devices so you can test two
Android phones against each other.

**Configuration:**

To create a connection with a specific Android device you need:

- a device serial number (you can find it with `adb devices -l`)

If no serial number is given and two Android phones are present, they
will automatically be assigned.

Examples: 
```
python3 main.py --android-central 0123456789
```
```
python3 main.py
```

#### Testing with Android + Mynewt Nimble

See the setup for both IUTs above.

The tool supports using Android device along Mynewt device so you can
test them against each other.

**Configuration:**

To create a connection with a specific Android device you need:

- a device serial number (you can find it with `adb devices -l`)

Example: 
```
python3 main.py --android-central 0123456789 --use-mynewt
```

#### Preparing a test run

In the current version of this tool preparing a test run is very simple.
Everything can be configured inside `main.py` file.

Firstly, configure and create objects representing connections to your
IUTs as described above. Then prepare a test suite. BTPTesterCore
uses Python's unittest framework to run tests. First create a
`unittest.TestSuite() object like so:

```
suite = unittest.TestSuite()
```

Then you can start adding testcases by specifying a testcase name
explicitly:

```
suite.addTest(GapTestCase('test_btp_GAP_CONN_DCON_1', mynewt, android))
```

or by using a helper function that returns all testcases inside a file:

```
suite.addTests(GapTestCase.init_testcases(mynewt, android))
suite.addTests(GattTestCase.init_testcases(mynewt, android))
```

Please note that when adding testcases we initialize each testcase
object by passing IUTs as the parameters.

Lastly, create a test runner and run the test suite:

```
runner = unittest.TextTestRunner(verbosity=2)
runner.run(suite())
```

A working example can be found in `main.py` file. It can be run also from test.sh script.
Running `main.py` from `test.sh` will generate two `.log` files: `logger_traces.log` with
history of run functions and their outputs and `test.log` with reports of executed tests.
If running test from shell script, user can define time when  tests will be run. At accepts
many time formats,  i.e. date in format 2020-04-30, time in form 09:20 or 0920 and 
now + n minute, hour, day.

#### Testcase naming convention

All testcases should be named according to the following format:

```
test_btp_<PROFILE>_<GROUP>_<FEATURE>_<NUM>
```

#### Running a specific test or suite

Tests can be specified as arguments when running the tool.
If no specific test is passed as argument, all tests present in main.py will run.

The format should be:
```
--test <TEST_SUITE>#<TEST>
```

Examples: 
```
python3 main.py --test GattTestCase#test_btp_GATT_CL_GAD_1
```
```
python3 main.py --test GapTestCase
```

#### Required static GATT Database

The IUT should implement the following static GATT database to pass
the defined GATT testcases:

```
Service
    UUID: 0000001E-8C26-476F-89A7-A108033A69C7
Service
    UUID: 00000001-8C26-476F-89A7-A108033A69C7
    Included: 0000001E-0000-1000-8000-00805f9b34fb
Characteristic
    UUID: 00000006-8C26-476F-89A7-A108033A69C7
    Property: READ | WRITE
    Permission: READ | WRITE
    Value: 1 byte length
Descriptor
    UUID: 0000000B-8C26-476F-89A7-A108033A69C7
    Permission: READ | WRITE
    Value: 1 byte length
Descriptor
    UUID: 0000001B-8C26-476F-89A7-A108033A69C7
    Permission: READ | WRITE
    Value: 100 byte length
Characteristic
    UUID: 00000015-8C26-476F-89A7-A108033A69C7
    Property: READ | WRITE
    Permission: READ | WRITE
    Value: 100 byte length
Characteristic
    UUID: 00000025-8C26-476F-89A7-A108033A69C7
    Property: NOTIFY | INDICATE
    Permission: READ
    Value: 1 byte length
Descriptor
    UUID: 2902 (CCCD)
    Permission: READ | WRITE
```

#### Support for other systems and devices

It is possible to use this tool with other systems and devices. The only
requirement is to use Bluetooth Testing Protocol for communication. Adding
support for Zephyr OS should be trivial, because it has a very similar 
app to Mynewt's bttester - https://github.com/zephyrproject-rtos/zephyr/tree/master/tests/bluetooth/tester.

There are also plans to add support for testing with iOS and Bluez.


----

This is a very early version of this tool so there may be issues and missing
features. Feel free to test it and submit PRs, feature requests or report 
problems you find.

