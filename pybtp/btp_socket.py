import logging
import os
import socket

from .parser import dec_hdr, dec_data, HDR_LEN

log = logging.debug


class BTPSocket:

    def __init__(self, socket_address):
        self.socket_address = socket_address
        self.sock = None
        self.conn = None
        self.addr = None

    def open(self):
        if os.path.exists(self.socket_address):
            os.remove(self.socket_address)

        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(self.socket_address)

        # queue only one connection
        self.sock.listen(1)

    def accept(self, timeout=10.0):
        self.sock.settimeout(timeout)
        self.conn, self.addr = self.sock.accept()
        self.sock.settimeout(None)

    def read(self, timeout=20.0):
        toread_hdr_len = HDR_LEN
        hdr = bytearray(toread_hdr_len)
        hdr_memview = memoryview(hdr)
        self.conn.settimeout(timeout)

        # Gather frame header
        while toread_hdr_len:
            nbytes = self.conn.recv_into(hdr_memview, toread_hdr_len)
            hdr_memview = hdr_memview[nbytes:]
            toread_hdr_len -= nbytes

        tuple_hdr = dec_hdr(hdr)
        toread_data_len = tuple_hdr.data_len

        logging.debug("Received: hdr: %r %r", tuple_hdr, hdr)

        data = bytearray(toread_data_len)
        data_memview = memoryview(data)

        # Gather optional frame data
        while toread_data_len:
            nbytes = self.conn.recv_into(data_memview, toread_data_len)
            data_memview = data_memview[nbytes:]
            toread_data_len -= nbytes

        tuple_data = dec_data(data)
        log("Received data: %r, %r", tuple_data, data)
        self.conn.settimeout(None)

        return tuple_hdr, tuple_data

    def send(self, data):
        self.conn.send(data)

    def close(self):
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()

        self.sock = None
        self.conn = None
        self.addr = None
