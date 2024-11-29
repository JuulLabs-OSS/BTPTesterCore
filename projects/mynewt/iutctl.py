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

import socket
import subprocess
import logging
import shlex
import time
import serial

from common.board import Board
from common.iutctl import IutCtl
from common.rtt2pty import RTT2PTY
from pybtp import defs
from pybtp.btp import BTPEventHandler
from pybtp.btp_socket import BTPSocket
from pybtp.btp_worker import BTPWorker
from stack.stack import Stack
from pybtp.types import BTPError
from projects.mynewt.boards import get_build_and_flash

log = logging.debug

# BTP communication transport: unix domain socket file name
BTP_ADDRESS = "/tmp/bt-stack-tester"


class MynewtCtl(IutCtl):
    """Mynewt OS Control Class"""

    def __init__(self, board: Board, gdb=None):
        log("%s.%s board=%r", self.__class__,
            self.__init__.__name__, board)

        self.board = board
        self.id = self.board.id
        self.btp_address = BTP_ADDRESS + '-' + str(self.id)
        self._socat_process = None
        self._btp_socket = None
        self._btp_worker = None
        self.gdb = gdb

        self.log_filename = "iut-mynewt-{}.log".format(self.id)
        self.log_file = open(self.log_filename, "w")

        self._stack = Stack()
        self._event_handler = BTPEventHandler(self)

    @property
    def btp_worker(self):
        return self._btp_worker

    @property
    def event_handler(self):
        return self._event_handler

    @property
    def stack(self):
        return self._stack

    def build_and_flash(self, board_name, project_path):
        overlay = {}
        build_and_flash = get_build_and_flash(board_name)
        try:
            build_and_flash(project_path, board_name, overlay, self.board.sn)
        except:
            raise

    def flush_serial(self):
        log("%s.%s", self.__class__, self.flush_serial.__name__)
        # Try to read data or timeout
        ser = serial.Serial(port=self.board.serial_port,
                            baudrate=self.board.serial_baudrate, timeout=1)
        ser.read(99999)
        ser.close()

    def start(self):
        """Starts the Mynewt OS"""

        log("%s.%s", self.__class__, self.start.__name__)

        self._btp_socket = BTPSocket(self.btp_address)
        self._btp_worker = BTPWorker(self._btp_socket, 'RxWorkerMynewt-' +
                                     str(self.id))

        self._event_handler = BTPEventHandler(self)

        self._btp_worker.open()
        self._btp_worker.register_event_handler(self._event_handler)

        self.flush_serial()

        socat_cmd = ("socat -x -v %s,rawer,b%d UNIX-CONNECT:%s" %
                     (self.board.serial_port, self.board.serial_baudrate, self.btp_address))

        log("Starting socat process: %s", socat_cmd)

        self._socat_process = subprocess.Popen(shlex.split(socat_cmd),
                                               shell=False,
                                               stdout=self.log_file,
                                               stderr=self.log_file)

        self._btp_worker.accept()

    def reset(self):
        """Restart IUT related processes and reset the IUT"""
        log("%s.%s", self.__class__, self.reset.__name__)

        self.stop()
        self.start()
        self.flush_serial()

        if not self.board:
            return

        if not self.gdb:
            self.board.reset(self.log_file)

    def wait_iut_ready_event(self):
        """Wait until IUT sends ready event after power up"""
        self.reset()

        if not self.gdb:
            tuple_hdr, tuple_data = self._btp_worker.read()
            if (tuple_hdr.svc_id != defs.BTP_SERVICE_ID_CORE or
                    tuple_hdr.op != defs.CORE_EV_IUT_READY):
                err = BTPError("Failed to get ready event")
                log("Unexpected event received (%s), expected IUT ready!", err)
                raise err
            else:
                log("IUT ready event received OK")

    def stop(self):
        """Stop IUT related processes"""
        log("%s.%s", self.__class__, self.stop.__name__)

        if self._btp_worker:
            self._btp_worker.close()
            self._btp_worker = None
            self._btp_socket = None

        if self._socat_process and self._socat_process.poll() is None:
            self._socat_process.terminate()
            self._socat_process.wait()

        if self._event_handler:
            self._event_handler.clear_listeners()

    def get_type(self):
        return self.TYPE_MYNEWT

    def __str__(self):
        return f"MynewtCtl board id: {self.board.id}, sn: {self.board.sn}"
