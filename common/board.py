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
import shlex
import subprocess
import re

log = logging.debug

ID = 0


def get_next_id():
    global ID
    next_id = ID
    ID += 1
    return next_id


def nrf_list_devices_cmd():
    return 'nrfjprog -i'


def nrf_reset_cmd(sn=None):
    cmd = 'nrfjprog -r'
    if sn:
        cmd += ' -s {}'.format(sn)

    return cmd


def nrf_get_tty_by_sn(sn):
    serial_devices = {}
    ls = subprocess.Popen("ls -l /dev/serial/by-id",
                          stdout=subprocess.PIPE,
                          shell=True)
    awk = subprocess.Popen("awk '{if (NF > 5) print $(NF-2), $NF}'",
                           stdin=ls.stdout,
                           stdout=subprocess.PIPE,
                           shell=True)
    end_of_pipe = awk.stdout
    for line in end_of_pipe:
        line = line.decode()
        _, path = line.rstrip().split(" ")
        if not 'usb-SEGGER_J-Link' in line:
            continue
        serial_num = re.match(".*?J-Link_(.*)-.*", line).group(1)
        port_number = re.match(".*?if([0-9]{2})", line).group(1)
        if port_number != "00":
            continue
        serial_devices[serial_num] = path

    for device, serial in serial_devices.items():
        if sn in device:
            return '/dev/serial/by-id/' + serial

    raise ValueError("No available device for serial number " + sn)


def list_available_boards():
    output = subprocess.check_output(shlex.split(nrf_list_devices_cmd()))
    devices = output.decode().splitlines()
    return devices


DFLT_SERIAL_BAUDRATE = 115200


class Board:
    def __init__(self):
        self.log_file = None
        self.reset_cmd = None
        self.id = None
        self.serial_port = None
        self.serial_baudrate = None

    def reset(self, log_file):
        log("About to reset DUT: %r", self.reset_cmd)

        assert self.reset_cmd

        reset_process = subprocess.Popen(shlex.split(self.reset_cmd),
                                         shell=False,
                                         stdout=log_file,
                                         stderr=log_file)

        if reset_process.wait():
            logging.error("reset failed")


class NordicBoard(Board):
    def __init__(self, sn=None, serial_baudrate=DFLT_SERIAL_BAUDRATE):
        super().__init__()
        boards = list_available_boards()
        self.id = get_next_id()
        if sn:
            self.sn = sn
        else:
            self.sn = boards[self.id]

        self.reset_cmd = nrf_reset_cmd(self.sn)
        self.serial_port = nrf_get_tty_by_sn(self.sn)
        self.serial_baudrate = serial_baudrate
