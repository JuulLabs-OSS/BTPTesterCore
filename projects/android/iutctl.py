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
          "bounds=\"\[(\d+),(\d+)\]\[(\d+),(\d+)\]\"/' {}".format(
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
    subprocess.check_call(_adb_prefix(sn) + cmd2, shell=True)

    # TODO: Find a better way to parse the view file so we dont have to
    #  do it twice
    coords = _find_button_coords('OK', view_file)
    if not coords:
        coords = _find_button_coords('PAIR', view_file)

    cmd4 = "shell input tap {}".format(coords)
    subprocess.check_call(_adb_prefix(sn) + cmd4, shell=True)


def _adb_stop_app(sn):
    cmd = "am force-stop com.juul.btptesterandroid"
    subprocess.check_call(_adb_prefix(sn) + cmd, shell=True)


def _adb_start_app(sn):
    cmd = "am start -n com.juul.btptesterandroid/com.juul.btptesterandroid" \
          ".MainActivity "
    subprocess.check_call(_adb_prefix(sn) + cmd, shell=True)


def _adb_open_bluetooth_settings(sn):
    cmd = "shell am start -S com.android.settings/com.android.settings" \
          ".bluetooth.BluetoothSettings "
    subprocess.check_call(_adb_prefix(sn) + cmd, shell=True)


def _adb_get_ip(sn):
    cmd = "shell ip addr show wlan0 | grep \"inet\\s\" | awk '{print $2}' | " \
          "awk -F'/' '{print $1}' "
    return subprocess.check_output(_adb_prefix(sn) + cmd,
                                   shell=True).decode().strip()


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

        self._btp_socket = BTPWebSocket(self.host, self.port)
        self._btp_worker = BTPWorker(self._btp_socket, 'RxWorkerAndroid-' +
                                     self.serial_num)
        self._btp_worker.open()
        self._btp_worker.register_event_handler(self._event_handler)
        self._btp_worker.accept()

    def reset(self):
        # _adb_stop_app()
        # _adb_start_app()
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
