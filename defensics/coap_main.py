import sys
from os.path import dirname, join, abspath

sys.path.insert(0, abspath(join(dirname(__file__), '..')))

import logging
import signal
from optparse import OptionParser, make_option

from defensics.coap_automation_handler import CoapAutomationHandler


import coap_cfg



def main():
    format = ("%(asctime)s %(name)-20s %(levelname)s %(threadName)-40s "
              "%(filename)-25s %(lineno)-5s %(funcName)-25s : %(message)s")
    logging.basicConfig(level=logging.DEBUG, format=format, filename=coap_cfg.log_filename_temp)

    logging.debug("Starting CoAP proxy")

    signal.signal(signal.SIGINT, signal.SIG_DFL)

    option_list = [
        make_option("-i", "--device", action="store",
                    type="string", dest="dev_id", default='hci0'),
    ]
    parser = OptionParser(option_list=option_list)

    (options, args) = parser.parse_args()

    instrumentation_hdl = CoapAutomationHandler(options)
    instrumentation_hdl.make_server('localhost', 8000)



if __name__ == "__main__":
    main()
