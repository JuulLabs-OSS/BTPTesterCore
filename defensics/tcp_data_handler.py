import threading
import logging

from defensics.coap_proxy import CoapProxy
from defensics.tcp_server import TCPServer


class DataHandler(threading.Thread):
    def __init__(self, proxy: CoapProxy, tcp_server: TCPServer):
        super().__init__()
        self.proxy = proxy
        self.tcp_server = tcp_server
        logging.debug('local proxy: ' + str(self.proxy) + 'global proxy: ' + str(proxy))

    def run(self):
        rc = 1
        while rc != 0:
            rc = self.proxy.run()
            logging.debug('Proxy retry')
        logging.debug(str(self.proxy.device_iface) + str(self.proxy.req_char_iface) + str(self.proxy.rsp_char_iface))
        self.tcp_server.start()

        for data in self.tcp_server.recv():
            if self.proxy.is_ready():
                try:
                    rsp = self.proxy.send(data)
                    self.tcp_server.send(rsp)
                except TimeoutError:
                    logging.debug("Response timeout!")
                    # because proxy isn't run in separate process, it can easily be restarted
                    self.proxy.run()
                    logging.debug("Reconnecting")
            else:
                logging.error('proxy not ready')
                self.proxy.run()
