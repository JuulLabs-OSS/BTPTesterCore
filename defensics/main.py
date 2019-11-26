import logging
import time
from http.server import HTTPServer
from instrumentation_server import *

from defensics.btp_automation_handler import BTPAutomationHandler
from defensics.instrumentation_server import MakeInstrumentationServer
from projects.mynewt.iutctl import MynewtCtl

HOST_NAME = 'localhost'
PORT_NUMBER = 8000

if __name__ == '__main__':
    print("Starting instrumentation server")
    format = ("%(asctime)s %(name)-20s %(levelname)s %(threadName)-40s "
              "%(filename)-25s %(lineno)-5s %(funcName)-25s : %(message)s")
    logging.basicConfig(level=logging.DEBUG,
                        format=format)

    iut = MynewtCtl('/dev/ttyACM0', '683414473')
    automation_hdl = BTPAutomationHandler(iut)
    automation_hdl.start()

    httpd = HTTPServer((HOST_NAME, PORT_NUMBER),
                       MakeInstrumentationServer(automation_hdl))
    print(time.asctime(), 'Server Starts - %s:%s' % (HOST_NAME, PORT_NUMBER))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print(time.asctime(), 'Server Stops - %s:%s' % (HOST_NAME, PORT_NUMBER))

    automation_hdl.stop()
