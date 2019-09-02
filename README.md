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

#### Testing with Mynewt Nimble

To test with Mynewt Nimble the Device Under Test should run 
[bttester](https://github.com/apache/mynewt-nimble/tree/master/apps/bttester) 
app from Apache Mynewt Nimble repository. It uses serial port to communicate with 
BTPTesterCore app running on a computer. Testing with Mynewt relies on 
`nrfjprog` CLI app for listing and resetting devices. That means only 
Nordic nRF5x devices are supported right now. Adding support for other 
devices and transports should be fairly simple so feel free to submit PRs.

###### Configuration:

To create a connection with a Mynewt device you need:

- a serial port
- a device serial number

Example: 
```
MynewtCtl('/dev/ttyACM0', '683xxxxxx')
```
    
#### Testing with Android

To test with Android device you should use [BTPTesterAndroid](https://github.com/JuulLabs-OSS/BTPTesterAndroid)
 \- a dedicated Bluetooth testing app. It uses WebSocket technology to
communicate with the Core app. The Android app runs a WebSocket server
(which is a bit unusual, typically a mobile device is the client) and
BTPTesterCore runs a WebSocket client that connects to the Android 
app. When the connection is established, BTP packets can be sent
in both directions.
    
###### Configuration:

To create a connection with an Android device you need:

- an IP address and port (by default the BTPTesterAndroid app uses 8765)

Example: 
```
AndroidCtl('192.168.xxx.xxx', 8765)
```

#### Support for other systems and devices

It is possible to use this tool with other systems and devices. The only
requirement is to use Bluetooth Testing Protocol for communication. Adding
support for Zephyr OS should be trivial, because it has a very similar 
app to Mynewt's bttester - https://github.com/zephyrproject-rtos/zephyr/tree/master/tests/bluetooth/tester.

There are also plans to add support for testing with iOS and Bluez.


#### 

This is a very early version of this tool so there may be issue and missing
features. Feel free to test it and submit PRs, feature requests or report 
problems you find.

