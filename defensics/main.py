import sys
from os.path import dirname, join, abspath
sys.path.insert(0, abspath(join(dirname(__file__), '..')))

import argparse
import logging
import time
from http.server import HTTPServer

from common.board import NordicBoard
from defensics.btp_automation_handler import BTPAutomationHandler
from defensics.instrumentation_server import MakeInstrumentationServer
from defensics.tester_config import TesterConfig
from projects.mynewt.iutctl import MynewtCtl

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Defensics instrumentation server')
    parser.add_argument('--hostname', help='Host name for the instumentation HTTP server (default: localhost)',
                        action='store', default='localhost')
    parser.add_argument('-p', '--port', help='Port number for the instumentation HTTP server (default: 8000)',
                        action='store', default=8000)
    parser.add_argument('-i', '--index', help='Index of the Bluetooth controller for Defensics (default: 0)',
                        action='store', default=0)
    parser.add_argument('-s', '--sn', help='Serial number of a Nordic board to use (default: None, system will choose'
                                           'automatically)',
                        action='store', default=None)
    args = parser.parse_args()

    print("Starting instrumentation server")
    format = ("%(asctime)s %(name)-20s %(levelname)s %(threadName)-40s "
              "%(filename)-25s %(lineno)-5s %(funcName)-25s : %(message)s")
    logging.basicConfig(level=logging.DEBUG, format=format)

    board = NordicBoard(args.sn)
    iut = MynewtCtl(board)
    tester_config = TesterConfig(args.index)
    automation_hdl = BTPAutomationHandler(iut, tester_config)
    automation_hdl.start()

    httpd = HTTPServer((args.hostname, args.port),
                       MakeInstrumentationServer(automation_hdl))
    print(time.asctime(), 'Server Starts - %s:%s' % (args.hostname, args.port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print(time.asctime(), 'Server Stops - %s:%s' % (args.hostname, args.port))

    automation_hdl.stop()
