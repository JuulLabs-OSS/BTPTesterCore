#!/usr/bin/env python3
import time
from http.server import HTTPServer
import instrumentation_server

HOST_NAME = '192.168.9.117'
PORT_NUMBER = 8000

if __name__ == '__main__':
    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), instrumentation_server.InstrumentationServer)
    print(time.asctime(), 'Server Starts - %s:%s' % (HOST_NAME, PORT_NUMBER))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print(time.asctime(), 'Server Stops - %s:%s' % (HOST_NAME, PORT_NUMBER))
