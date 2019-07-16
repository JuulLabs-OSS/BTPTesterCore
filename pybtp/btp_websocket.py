import asyncio
import concurrent
import logging
import socket
import threading
import time

import websockets

from .parser import dec_hdr, dec_data, HDR_LEN

log = logging.debug


class WebSocketThread(threading.Thread):
    def __init__(self, host, port):
        super(WebSocketThread, self).__init__(name="WebSocketThread")
        self.host = host
        self.port = port

        self.websocket = None
        self.loop = None
        self.stoprequest = threading.Event()

    @asyncio.coroutine
    def _connect(self):
        return (yield from websockets.connect('ws://{}:{}/'.format(self.host,
                                                                   self.port)))

    def connect(self, timeout=None):
        future = asyncio.run_coroutine_threadsafe(self._connect(), self.loop)
        self.websocket = future.result(timeout)

    def send(self, message, timeout=None):
        future = asyncio.run_coroutine_threadsafe(self.websocket.send(message),
                                                  self.loop)
        try:
            return future.result(timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise socket.timeout

    def recv(self, timeout=None):
        future = asyncio.run_coroutine_threadsafe(self.websocket.recv(),
                                                  self.loop)
        try:
            return future.result(timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise socket.timeout

    def _exception_handler(self, loop, context):
        logging.debug("%s %r %r", self._exception_handler.__name__,
                      loop, context)
        exc = context["exception"]
        logging.debug("%s %r", self._exception_handler.__name__, exc)
        loop.stop()

    def run(self):
        logging.debug("%s", self.run.__name__)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        self.loop.set_exception_handler(self._exception_handler)
        self.loop.run_forever()

    @asyncio.coroutine
    def _close(self):
        yield from self.websocket.close()

    def join(self, timeout=None):
        self.stoprequest.set()
        if self.websocket:
            future = asyncio.run_coroutine_threadsafe(self._close(),
                                                      self.loop)
            future.result()
        self.loop.call_soon_threadsafe(self.loop.stop)
        super(WebSocketThread, self).join(timeout)


class BTPWebSocket:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.websocket_task = None

    def open(self):
        self.websocket_task = WebSocketThread(self.host, self.port)
        self.websocket_task.start()
        time.sleep(1)

    def accept(self, timeout=10.0):
        self.websocket_task.connect(timeout)

    def read(self, timeout=20.0):
        raw_data = self.websocket_task.recv(timeout)

        hdr = raw_data[:HDR_LEN]
        tuple_hdr = dec_hdr(hdr)
        data_len = tuple_hdr.data_len

        logging.debug("Received: hdr: %r %r", tuple_hdr, hdr)

        assert (len(raw_data) == HDR_LEN + data_len)

        data = raw_data[HDR_LEN:]
        tuple_data = dec_data(data)

        log("Received data: %r, %r", tuple_data, data)

        return tuple_hdr, tuple_data

    def send(self, data):
        self.websocket_task.send(data)

    def close(self):
        self.websocket_task.join()
