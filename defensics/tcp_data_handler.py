import threading
import logging
import time

from defensics.coap_proxy import CoapProxy
from defensics.tcp_server import TCPServer
import dbus
import subprocess
from coap_config import *

class DataHandler(threading.Thread):
    def __init__(self, proxy: CoapProxy, tcp_server: TCPServer):
        super().__init__()
        self.proxy = proxy
        self.tcp_server = tcp_server
        self.stop_data_handler = threading.Event()
        self.errors = []
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

    # This function mocks response for CSM and Ping messages.
    def mock_csm(self, data):
        if skip_csm and (b'q\xe1\x01\xffsample' in data or data == b'\x01\xe2\x02'):
            rsp = b'\x00\xa3'
            self.tcp_server.send(rsp)
            return False
        else:
            return True


    def _handle_dbus_exception(self, exception):
        logging.debug(exception.args)

        if 'Did not receive a reply' in exception.args[0]:
            # This error is mostly caused by losing connection with IUT (it crashed or disconnected by itself)
            # Restart proxy to reestablish connections
            self.stop_data_handler.set()
        elif 'Not connected' in exception.args[0]:
            # if not connected - reconnect. Skip rest of data, as it's continuation of previously
            # sent packets
            self.stop_data_handler.set()
        elif 'Operation failed with ATT error:' in exception.args[0]:
            # receiving ATT error means that rest of data is ignored by IUT and can e skipped
            pass
        elif 'Resource Not Ready' in exception.args[0]:
            self.stop_data_handler.set()
        elif 'Method "WriteValue" with signature "aya{sv}" on interface "org.bluez.GattCharacteristic1" doesn\'t exist\n':
            self.stop_data_handler.set()

    def run(self):
        try:
            self.proxy.run()
        except dbus.exceptions.DBusException as ex:
            self.errors.append({'proxy', ex})
            print(ex.args[0])
        self.stop_data_handler.clear()
        self.tcp_server.start()
        logging.debug('running data handler')
        while True:
            while not self.stop_data_handler.is_set():
                data = self.tcp_server.recv()
                if self.mock_csm(data):
                    try:
                        # Maximum of what we can send at once is 512, because
                        # that is maximum size of characteristic. Attempts to
                        # send larger payloads will result in error (like
                        # "invalid length", "not likely"), losing connection with
                        # DUT or, in extreme cases, locking of BlueZ
                        to_send = [data[i:i+512] for i in range(0, len(data), 512)]
                        for d in to_send:
                            rsp = self.proxy.send(d)
                            self.tcp_server.send(rsp)
                    except TimeoutError:
                        # TimeoutError is generated when no response is received, but it isn't expected for every packet
                        pass
                    except dbus.exceptions.DBusException as ex:
                        self.errors.append({'proxy', ex})
                        logging.debug(ex.args[0])
                        self._handle_dbus_exception(ex)
                    except Exception as ex:
                        self.errors.append({'tcp_server', ex})
                        logging.debug(ex.args[0])
                        self.stop_data_handler.set()
            # Teardown setup
            # restart BT controller before test
            logging.debug('restarting radio')
            cmd = ['sudo', '-S', 'service', 'bluetooth', 'restart']
            process = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            process.communicate(input=pwd.encode())[0].decode()
            # Function return doesn't mean that we can access radio instantly,
            # give some time for it to restart
            time.sleep(1)
            try:
                self.proxy.run()
            except dbus.exceptions.DBusException as ex:
                self.errors.append({'proxy', ex})
                print(ex.args[0])
            else:
                self.stop_data_handler.clear()
