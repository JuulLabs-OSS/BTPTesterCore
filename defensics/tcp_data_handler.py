import threading
import logging

from defensics.coap_proxy import CoapProxy
from defensics.tcp_server import TCPServer
import dbus


class DataHandler(threading.Thread):
    def __init__(self, proxy: CoapProxy, tcp_server: TCPServer):
        super().__init__()
        self.proxy = proxy
        self.tcp_server = tcp_server
        self.skipping = False
        logging.debug('local proxy: ' + str(self.proxy) + 'global proxy: ' + str(proxy))

    def _run_proxy(self):
        tries = 1
        rc = self.proxy.run()
        while rc != 0 and tries <= 10:
            rc = self.proxy.run()
            logging.debug('Retry starting proxy')
            tries += 1
        logging.debug(str(self.proxy.device_iface) + str(self.proxy.req_char_iface) + str(self.proxy.rsp_char_iface))
        return rc

    def _send_or_pass(self, data):
        if len(data) > 100 and self.skipping:
            return False
        else:
            return True

    def _handle_dbus_exception(self, exception):
        logging.debug(exception.args)
        if 'Did not receive a reply' in exception.args[0]:
            # This error is mostly caused by losing connection with IUT (it crashed or disconnected by itself)
            pass
        elif 'Not connected' in exception.args[0]:
            # if not connected - reconnect. Skip rest of data, as it's continuation of previously
            # sent packets
            self._run_proxy()
        elif 'Operation failed with ATT error:' in exception.args[0]:
            # receiving ATT error means that rest of data is ignored by IUT and can e skipped
            pass
        elif 'Resource Not Ready' in exception.args[0]:
            self._run_proxy()
        elif 'Method "WriteValue" with signature "aya{sv}" on interface "org.bluez.GattCharacteristic1" doesn\'t exist\n':
            self._run_proxy()
        self.skipping = True

    def run(self):
        self.tcp_server.start()
        logging.debug('running data handler')
        try:
            self._run_proxy()
        except dbus.exceptions.DBusException as ex:
            self._handle_dbus_exception(ex)

        for data in self.tcp_server.recv():
            if self.proxy.is_ready():
                # skipping long data packets, as they're continuation of previously sent long data. Shorter ones
                # might be beginning of new data, so don't ignore them and cancel skip.
                if self._send_or_pass(data):
                    try:
                        rsp = self.proxy.send(data)
                        self.tcp_server.send(rsp)
                    except TimeoutError:
                        # TimeoutError is generated when no response is received, but it isn't expected for every packet
                        pass
                    except dbus.exceptions.DBusException as ex:
                        self._handle_dbus_exception(ex)
            else:
                logging.error('proxy broke, restarting...')
                rc = self._run_proxy()
                if rc != 0:
                    logging.error('could not start proxy, aborting...')
                    return
