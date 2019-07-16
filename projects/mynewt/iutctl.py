import socket
import subprocess
import logging
import shlex
import time

from common.board import Board
from common.iutctl import IutCtl
from common.rtt2pty import RTT2PTY
from pybtp import defs
from pybtp.btp import BTPEventHandler
from pybtp.btp_socket import BTPSocket
from pybtp.btp_worker import BTPWorker
from stack.stack import Stack
from pybtp.types import BTPError

log = logging.debug

# BTP communication transport: unix domain socket file name
BTP_ADDRESS = "/tmp/bt-stack-tester"


class MynewtCtl(IutCtl):
    """Mynewt OS Control Class"""

    def __init__(self, tty_file, id):
        log("%s.%s tty_file=%s id=%s",
            self.__class__, self.__init__.__name__, tty_file, id)

        self.id = id
        self.btp_address = BTP_ADDRESS + '-' + str(self.id)
        self.tty_file = tty_file
        self.socat_process = None
        self._btp_socket = None
        self._btp_worker = None
        self.rtt = None

        self.log_filename = "iut-mynewt-{}.log".format(id)
        self.log_file = open(self.log_filename, "w")

        self.board = Board(id, "nrf52", self.log_file)

        self._stack = Stack()
        self.event_handler = BTPEventHandler(self)


    @property
    def btp_worker(self):
        return self._btp_worker

    @property
    def stack(self):
        return self._stack

    @staticmethod
    def init_rtt(board_id):
        log("%s.%s board_id=%s",
            __class__, __class__.init_rtt.__name__, board_id)

        rtt = RTT2PTY(board_id, "bttester")
        rtt.start()
        time.sleep(1)
        if not rtt.is_running():
            raise Exception("RTT2PTY failed")

        iut = MynewtCtl(rtt.get_pty_file(), board_id)
        iut.rtt = rtt
        return iut

    def start(self):
        """Starts the Mynewt OS"""

        log("%s.%s", self.__class__, self.start.__name__)

        self._btp_socket = BTPSocket(self.btp_address)
        self._btp_worker = BTPWorker(self._btp_socket, 'RxWorkerMynewt')
        self._btp_worker.open()
        self._btp_worker.register_event_handler(self.event_handler)

        socat_cmd = ("socat -x -v %s,rawer,b115200 UNIX-CONNECT:%s" %
                     (self.tty_file, self.btp_address))

        log("Starting socat process: %s", socat_cmd)

        self.socat_process = subprocess.Popen(shlex.split(socat_cmd),
                                              shell=False,
                                              stdout=self.log_file,
                                              stderr=self.log_file)

        self._btp_worker.accept()

        # Flush btp socket
        self.reset()
        try:
            self._btp_worker.read(timeout=1)
        except socket.timeout:
            pass

    def reset(self):
        if not self.board:
            return

        if self.rtt:
            self.rtt.cleanup()
        self.board.reset()
        if self.rtt:
            self.rtt.start()

    def wait_iut_ready_event(self):
        """Wait until IUT sends ready event after power up"""
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
        """Powers off the Mynewt OS"""
        log("%s.%s", self.__class__, self.stop.__name__)

        if self._btp_worker:
            self._btp_worker.close()
            self._btp_worker = None
            self._btp_socket = None

        if self.socat_process and self.socat_process.poll() is None:
            self.socat_process.terminate()
            self.socat_process.wait()

        if self.rtt:
            self.rtt.cleanup()
            self.rtt = None
