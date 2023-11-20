#
# Copyright (c) 2019 JUUL Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging
import subprocess

from common.iutctl import IutCtl
from pybtp import defs
from pybtp.btp import BTPEventHandler
from pybtp.btp_websocket import BTPWebSocket
from pybtp.btp_worker import BTPWorker
from pybtp.types import BTPError
from stack.stack import Stack

log = logging.debug


def _adb_prefix(sn):
    return "adb {}".format('-s {} '.format(sn) if sn else '')


def _find_button_coords(text, view_file):
    cmd = "perl -ne 'printf \"%d %d\n\", ($1+$3)/2, " \
          "($2+$4)/2 if /text=\"{}\"[^>]*" \
          "bounds=\"\[(\d+),(\d+)\]\[(\d+),(\d+)\]\"/i' {}".format(
        text, view_file)
    coords = subprocess.check_output(cmd, shell=True).decode().strip()
    return coords


def _adb_tap_ok(sn):
    # TODO: Handle different button text than "OK" or find a better way to
    #  automate pairing confirmation
    cmd1 = "shell uiautomator dump | grep -oP '[^ ]+.xml'"
    file = subprocess.check_output(_adb_prefix(sn) + cmd1,
                                   shell=True).decode().strip()
    view_file = '/tmp/view-{}.xml'.format(sn)

    cmd2 = "pull {} {}".format(file, view_file)
    subprocess.check_call(_adb_prefix(sn) + cmd2, shell=True,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.STDOUT)

    # TODO: Find a better way to parse the view file so we dont have to
    #  do it twice
    coords = _find_button_coords('PAIR', view_file)
    if not coords:
        coords = _find_button_coords('OK', view_file)

    cmd4 = "shell input tap {}".format(coords)
    subprocess.check_call(_adb_prefix(sn) + cmd4, shell=True)


def _adb_stop_app(sn):
    cmd = "am force-stop com.juul.btptesterandroid"
    subprocess.check_call(_adb_prefix(sn) + cmd, shell=True)


def _adb_start_app(sn):
    cmd = "shell am start -n com.juul.btptesterandroid/com.juul.btptesterandroid" \
          ".MainActivity "
    subprocess.check_call(_adb_prefix(sn) + cmd, shell=True,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.STDOUT)

def _adb_stop_app(sn):
    cmd = "shell am force-stop com.juul.btptesterandroid"
    subprocess.check_call(_adb_prefix(sn) + cmd, shell=True,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.STDOUT)


def _adb_open_bluetooth_settings(sn):
    cmd = "shell am start -S com.android.settings/com.android.settings" \
          ".bluetooth.BluetoothSettings "
    subprocess.check_call(_adb_prefix(sn) + cmd, shell=True,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.STDOUT)

def _adb_close_bluetooth_settings(sn):
    cmd = "shell am force-stop com.android.settings"
    subprocess.check_call(_adb_prefix(sn) + cmd, shell=True,
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.STDOUT)


def _adb_get_ip(sn):
    cmd = "shell ip addr show wlan0 | grep \"inet\\s\" | awk '{print $2}' | " \
          "awk -F'/' '{print $1}' "
    return subprocess.check_output(_adb_prefix(sn) + cmd,
                                   shell=True).decode().strip()

def _adb_get_available_devices():
    cmd = "adb devices -l | grep \"product\" | awk '{print $1}'"
    return subprocess.check_output(cmd, shell=True).decode().strip().split('\n')

def _adb_wake_unlock(sn):
    cmd_check_unlocked = "shell dumpsys power | grep mHoldingDisplaySuspendBlocker"
    cmd_wake = "shell input keyevent KEYCODE_WAKEUP"
    cmd_unlock = "shell input keyevent KEYCODE_MENU"

    unlocked = subprocess.check_output(_adb_prefix(sn) + cmd_check_unlocked,
                                       shell=True).decode().strip().split('=')[1]
    if unlocked == "false":
        subprocess.check_call(_adb_prefix(sn) + cmd_wake + " && sleep .1 && " + _adb_prefix(sn) + cmd_unlock, shell=True)

def _adb_set_wake_timeout(sn, timeout):
    cmd = "shell settings put system screen_off_timeout " + str(timeout)
    subprocess.check_call(_adb_prefix(sn) + cmd, shell=True)





class AndroidCtl(IutCtl):
    def __init__(self, serial_num, host=None, port=None):
        log("%s.%s serial_num=%s host=%s port=%s",
            self.__class__, self.__init__.__name__, serial_num, host, port)

        self.serial_num = serial_num

        if host:
            self.host = host
        else:
            self.host = _adb_get_ip(self.serial_num)

        if port:
            self.port = port
        else:
            self.port = self.PORT_DEFAULT

        self._btp_socket = None
        self._btp_worker = None

        # self.log_filename = "iut-mynewt-{}.log".format(id)
        # self.log_file = open(self.log_filename, "w")

        self._stack = Stack()
        self._stack.set_pairing_consent_cb(lambda addr:
                                           _adb_tap_ok(self.serial_num))
        self._stack.set_passkey_confirm_cb(lambda addr, match:
                                           _adb_tap_ok(self.serial_num))
        self._event_handler = BTPEventHandler(self)

        # Unlock phone, set screen wake timeout
        _adb_set_wake_timeout(self.serial_num, 600000)
        _adb_wake_unlock(self.serial_num)

    @property
    def PORT_DEFAULT(self):
        return 8765

    @property
    def btp_worker(self):
        return self._btp_worker

    @property
    def event_handler(self):
        return self._event_handler

    @property
    def stack(self):
        return self._stack

    def start(self):
        log("%s.%s", self.__class__, self.start.__name__)

        _adb_start_app(self.serial_num)

        self._btp_socket = BTPWebSocket(self.host, self.port)
        self._btp_worker = BTPWorker(self._btp_socket, 'RxWorkerAndroid-' +
                                     self.serial_num)
        self._btp_worker.open()
        self._btp_worker.register_event_handler(self._event_handler)
        self._btp_worker.accept()

    def reset(self):
        self.stop()
        self.start()
        # When pairing with newer Android versions the pairing is confirmed
        # using a notification instead of a popup window. We are not able to
        # parse this notification. To work around it we open Bluetooth
        # settings activity. When in this activity Android displays
        # the popup window instead of the notification.
        _adb_open_bluetooth_settings(self.serial_num)
        pass

    def wait_iut_ready_event(self):
        self.reset()

        tuple_hdr, tuple_data = self._btp_worker.read()

        try:
            if (tuple_hdr.svc_id != defs.BTP_SERVICE_ID_CORE or
                    tuple_hdr.op != defs.CORE_EV_IUT_READY):
                raise BTPError("Failed to get ready event")
        except BTPError as err:
            log("Unexpected event received (%s), expected IUT ready!", err)
            self.stop()
        else:
            log("IUT ready event received OK")

    def stop(self):
        log("%s.%s", self.__class__, self.stop.__name__)

        if self._btp_worker:
            self._btp_worker.close()
            self._btp_worker = None
            self._btp_socket = None

        if self._event_handler:
            self._event_handler.clear_listeners()

        # Close the Android app and Bluetooth Settings in case a crash happened
        # and they are in a bad state from previous run.
        _adb_stop_app(self.serial_num)
        _adb_close_bluetooth_settings(self.serial_num)

    @classmethod
    def from_serials_or_auto(cls, central_serial, peripheral_serial):
        central = None
        peripheral = None
        available_devices = _adb_get_available_devices()

        if len(available_devices) == 0:
            return None, None

        if central_serial in available_devices:
            central = AndroidCtl(central_serial)
        if peripheral_serial in available_devices and peripheral_serial != central_serial:
            peripheral = AndroidCtl(peripheral_serial)

        if central is None:
            for serial in available_devices:
                if peripheral_serial != serial:
                    central_serial = serial
                    central = AndroidCtl(serial)
                    break
        if peripheral is None:
            for serial in available_devices:
                if central_serial != serial:
                    peripheral = AndroidCtl(serial)
                    break

        return central, peripheral

    def __str__(self):
        return f"AndroidCtl serial: {self.serial_num}, host: {self.host}, port: {self.port}"
