import sys
from os.path import dirname, join, abspath

sys.path.insert(0, abspath(join(dirname(__file__), '..')))

import logging
import signal
from optparse import OptionParser, make_option

import dbus
import dbus.mainloop.glib

from defensics.coap_automation_handler import CoapAutomationHandler
from defensics.coap_proxy import CoapProxy, DEVICE_ADDR
from defensics.udp_server import UDPServer

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject


def main():
    format = ("%(asctime)s %(name)-20s %(levelname)s %(threadName)-40s "
              "%(filename)-25s %(lineno)-5s %(funcName)-25s : %(message)s")
    logging.basicConfig(level=logging.DEBUG, format=format)

    logging.debug("Starting CoAP proxy")
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    option_list = [
        make_option("-i", "--device", action="store",
                    type="string", dest="dev_id", default='hci0'),
    ]
    parser = OptionParser(option_list=option_list)

    (options, args) = parser.parse_args()

    mainloop = GObject.MainLoop()
    udp = UDPServer('127.0.0.1', 5683)
    proxy = CoapProxy(DEVICE_ADDR, options.dev_id)

    automation = CoapAutomationHandler(proxy, udp)
    automation.start()

    mainloop.run()


if __name__ == "__main__":
    main()
