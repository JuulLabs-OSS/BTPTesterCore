import logging
import socket
import os


class TCPServer:
    def __init__(self, host='127.0.0.1', port=5683):
        super().__init__()
        self.host = host
        self.port = port
        self.addr = None
        self.sock = None
        self.conn = None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        logging.info("Listening on tcp %s:%s" % (self.host, self.port))
        try:
            self.sock.bind(('', self.port))
        except OSError:
            logging.error('OSError: unable to bind socket. Terminating...')
            os._exit(1)
        self.sock.listen(10)
        self.conn, self.addr = self.sock.accept()
        logging.info("Connecion address: %s, port %d", self.addr[0], self.addr[1])

    def recv(self):
        try:
            data = self.conn.recv(128 * 1024)
        except ConnectionResetError:
            logging.debug("Conn error")
            self.conn.close()
            self.start()
        logging.debug("Received %r bytes from %s" % (len(data), self.addr))
        return data

    def send(self, data):
        logging.debug("Sending %r bytes to %s", len(data), self.addr)
        try:
            self.conn.send(data)
        except (ConnectionResetError, BrokenPipeError):
            self.sock.listen(10)
            self.conn, self.addr = self.sock.accept()

    def close(self):
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
