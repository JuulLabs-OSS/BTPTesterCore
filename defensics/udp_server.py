import logging
import socket


class UDPServer:
    def __init__(self, host='127.0.0.1', port=5683):
        self.host = host
        self.port = port
        self.addr = None
        self.sock = None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        logging.info("Listening on udp %s:%s" % (self.host, self.port))
        self.sock.bind((self.host, self.port))

    def recv(self):
        while True:
            (data, addr) = self.sock.recvfrom(128 * 1024)
            logging.debug("Received %s from %s" % (data, addr))
            self.addr = addr
            yield data

    def send(self, data):
        logging.debug("Sending %s to %s" % (data, self.addr))
        self.sock.sendto(data, self.addr)
