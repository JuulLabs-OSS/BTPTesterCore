#
# auto-pts - The Bluetooth PTS Automation Framework
#
# Copyright (c) 2017, Intel Corporation.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
import binascii
import logging
import queue
import socket
import threading

from pybtp import defs
from pybtp.parser import enc_frame
from .types import BTPError

log = logging.debug


class BTPWorker:
    def __init__(self, btp_socket, name=None):
        self.btp_socket = btp_socket
        self._rx_queue = queue.Queue()
        self._running = threading.Event()

        self._rx_worker = threading.Thread(target=self._rx_task,
                                           name=name)
        self.read_timer = None
        self.event_handler_cb = None

    def open(self):
        self.btp_socket.open()

    def _rx_task(self):
        while self._running.is_set():
            try:
                data = self.btp_socket.read(timeout=1.0)

                hdr = data[0]
                if hdr.op >= 0x80:
                    # Do not put handled events on RX queue
                    if self.event_handler_cb:
                        ret = self.event_handler_cb(*data)
                        if ret is True:
                            continue

                self._rx_queue.put(data)
            except socket.timeout:
                pass

    @staticmethod
    def _read_timeout(flag):
        flag.clear()

    def read(self, timeout=20.0):
        logging.debug("%s", self.read.__name__)

        flag = threading.Event()
        flag.set()

        self.read_timer = threading.Timer(timeout, self._read_timeout, [flag])
        self.read_timer.start()

        while flag.is_set():
            if self._rx_queue.empty():
                continue

            self.read_timer.cancel()

            data = self._rx_queue.get()
            self._rx_queue.task_done()

            return data

        raise socket.timeout

    def send(self, svc_id, op, ctrl_index, data):
        logging.debug("%s, %r %r %r %r",
                      self.send.__name__, svc_id, op, ctrl_index, data)

        if isinstance(data, int):
            data = str(data)
            if len(data) == 1:
                data = "0%s" % data
                data = binascii.unhexlify(data)
        elif isinstance(data, str):
            data = data.encode()

        hex_data = binascii.hexlify(data)
        logging.debug("btpclient command: send %d %d %d %s",
                      svc_id, op, ctrl_index, hex_data)

        bin_data = enc_frame(svc_id, op, ctrl_index, data)

        logging.debug("sending frame %r", bin_data)

        self.btp_socket.send(bin_data)

    def send_wait_rsp(self, svc_id, op, ctrl_index, data, cb=None,
                      user_data=None):
        self.btp_socket.send(svc_id, op, ctrl_index, data)
        ret = True

        while ret:
            tuple_hdr, tuple_data = self.read()

            if tuple_hdr.svc_id != svc_id:
                raise BTPError(
                    "Incorrect service ID %s in the response, expected %s!" %
                    (tuple_hdr.svc_id, svc_id))

            if tuple_hdr.op == defs.BTP_STATUS:
                raise BTPError("Error opcode in response!")

            if op != tuple_hdr.op:
                raise BTPError(
                    "Invalid opcode 0x%.2x in the response, expected 0x%.2x!" %
                    (tuple_hdr.op, op))

            if cb and callable(cb):
                ret = cb(tuple_data, user_data)
            else:
                return tuple_data

    def _reset_rx_queue(self):
        while not self._rx_queue.empty():
            try:
                self._rx_queue.get_nowait()
            except queue.Empty:
                continue

            self._rx_queue.task_done()

    def accept(self, timeout=10.0):
        logging.debug("%s", self.accept.__name__)

        self.btp_socket.accept(timeout)

        self._running.set()
        self._rx_worker.start()

    def close(self):
        self._running.clear()

        if self._rx_worker.is_alive():
            self._rx_worker.join()

        if self.read_timer:
            self.read_timer.cancel()

        self._reset_rx_queue()

        self.btp_socket.close()

    def register_event_handler(self, event_handler):
        self.event_handler_cb = event_handler
