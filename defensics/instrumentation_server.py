import json
import logging
from http.server import BaseHTTPRequestHandler

from defensics.http_response import HTTPResponse

log = logging.debug


def MakeInstrumentationServer(automation_hdl):
    class InstrumentationServer(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self.automation_hdl = automation_hdl
            super(InstrumentationServer, self).__init__(*args, **kwargs)

        def do_POST(self):
            content_length = int(
                self.headers['Content-Length'])  # <--- Gets the size of data
            post_data = self.rfile.read(content_length).decode('utf-8')  # <--- Gets the data itself
            log("POST request: Path: {}; Body:{}".format(str(self.path), post_data))

            params = json.loads(post_data)
            self.automation_hdl.post(self.path, params)

            rsp = HTTPResponse()
            rsp.contents = self.automation_hdl.get_status().to_json()
            log("Response contents: {}".format(rsp.contents))

            self.respond({'rsp': rsp})

        def handle_http(self, handler):
            status_code = handler.get_status()

            self.send_response(status_code)

            if status_code == 200:
                content = handler.get_contents()
                self.send_header('Content-type', handler.get_content_type())
            else:
                content = "404 Not Found"

            self.end_headers()

            return bytes(content, 'UTF-8')

        def respond(self, opts):
            response = self.handle_http(opts['rsp'])
            self.wfile.write(response)

    return InstrumentationServer
