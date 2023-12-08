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

To get the serial number, use `nrfjprog -i`

Example BTPTester run:
```
python3 btptester.py --central mynewt 1050069955 --peripheral mynewt 1050069956
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

To get the serial number, use `adb devices -l`

Example:
```
python3 btptester.py --central android 13161JEC203758 --peripheral android 14161JEC203758
```

#### Adding new tests

BTPTesterCore uses Python's unittest framework to run tests.

You can add new tests either by adding them to existing test classes
like in `GapTestCase.py`, or creating a new profile class.

If you create a new test class, you'll need to add it to `btptester.py`
in the `create_suite` function so that a default run takes it.

Example:

```
suite.addTests(GapTestCase.init_testcases(iut1, iut2))
suite.addTests(GattTestCase.init_testcases(iut1, iut2))
suite.addTests(ProfileTestCase.init_testcases(iut1, iut2))
```

#### Testcase naming convention

All testcases should be named according to the following format:

```
test_btp_<PROFILE>_<GROUP>_<FEATURE>_<NUM>
```

#### Running a specific test or suite

Tests can be specified as arguments when running the tool.
If no specific test is passed as argument, all tests present
in `btptester.py` will run.

The format should be:
```
--test <TEST_SUITE>#<TEST>
```

Examples:
```
python3 btptester.py --central mynewt 1050069955 --peripheral android 13161JEC203758 --test GattTestCase#test_btp_GATT_CL_GAD_1
```
```
python3 btptester.py --central mynewt 1050069955 --peripheral android 13161JEC203758 --test GattTestCase
```

#### Other run options

##### `--rerun-reverse`

Specifying this will make the tests rerun and reverse central and peripheral IUTs.

##### `--run-count x`

Reruns x times.

##### `--rerun-until-failure`

Run the tests again after completion until one test fails.

##### `--fail-fast`

Stops the run at first failure.

#### Automation

You can use `btptester_cron.py` to start the cron script provided with this tool.
The cron script is able to run both scheduled jobs and pull requests jobs, using
a magic tag.

Detailled information about configuration can be found [here](cron/README.md).

##### Scheduled jobs

As long as the script is running, it will run configured scheduled jobs.

##### Pull requests jobs

As long as the script is running it will fetch comments from pull requests on
configured repos and if a magic tag is found, update the repo, fetch the pull
request, build and flash IUTs, then run BTPTester.

Example of magic tag: `#BTPTester run`

The `against=` argument can be added on the comment to specify which OS the
tester should take as second device (first device is of the specified OS in config).
**If not specified, the tester will choose the same OS as the firs one.**

Once the tests results are available, the script will post a comment on the
pull request.

Example of pull request magic tag comment:
```
#BTPTester run against=android
```

Example:
```
python3 btptester_cron.py cron/config.py
```

##### List available devices

You can get the list of configured OS directly from the pull request comments,
by using the magic tag `#BTPTester devices`.

Example of pull request magic tag comment:
```
#BTPTester devices
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

