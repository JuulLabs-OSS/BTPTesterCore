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

from common.iutctl import IutCtl
from pybtp import defs
from pybtp.btp import BTPEventHandler
from pybtp.btp_websocket import BTPWebSocket
from pybtp.btp_worker import BTPWorker
from pybtp.types import BTPError
from stack.stack import Stack

log = logging.debug


class AndroidCtl(IutCtl):
    def __init__(self, host, port):
        log("%s.%s host=%s port=%s",
            self.__class__, self.__init__.__name__, host, port)

        self.host = host
        self.port = port
        self._btp_socket = None
        self._btp_worker = None

        # self.log_filename = "iut-mynewt-{}.log".format(id)
        # self.log_file = open(self.log_filename, "w")

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

    def start(self):
        log("%s.%s", self.__class__, self.start.__name__)

        self._btp_socket = BTPWebSocket(self.host, self.port)
        self._btp_worker = BTPWorker(self._btp_socket, 'RxWorkerAndroid')
        self._btp_worker.open()
        self._btp_worker.register_event_handler(self._event_handler)
        self._btp_worker.accept()

    def reset(self):
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

