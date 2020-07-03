import threading
import logging

from defensics.coap_proxy import CoapProxy
from defensics.tcp_server import TCPServer

class DataHandler(threading.Thread):
    def __init__(self, proxy: CoapProxy, tcp_server: TCPServer):
        super().__init__()
        self.proxy = proxy
        self.tcp_server = tcp_server

    def run(self):
        self.tcp_server.start()
        self.proxy.run()

        for data in self.tcp_server.recv():
            if self.proxy.is_ready():
                try:
                    rsp = self.proxy.send(data)
                    self.tcp_server.send(rsp)
                except TimeoutError:
                    logging.debug("Response timeout!")
                    self.proxy.device_iface.Disconnect()
                    self.proxy.device_iface.Connect()
                    logging.debug("Reconnecting")
                    self.tcp_server.conn.close()
                    self.tcp_server.conn, self.tcp_server.addr = \
                        self.tcp_server.sock.accept()
            else:
                raise Exception("Proxy not ready")
