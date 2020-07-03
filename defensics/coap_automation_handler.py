import logging
import socket
import threading
from queue import Queue, Full
import asyncio
from http.server import HTTPServer
from multiprocessing import Process

from defensics.automation_status import AutomationStatus
from defensics.instrumentation_server import MakeInstrumentationServer
from stack.gap import BleAddress

TESTER_ADDR = BleAddress('001bdc069e49', 0)
TESTER_READ_HDL = '0x0003'
TESTER_WRITE_HDL = '0x0005'
TESTER_SERVICE_UUID = '180F'
TESTER_PASSKEY = '000000'

INSTR_STEP_BEFORE_RUN = '/before-run'
INSTR_STEP_BEFORE_CASE = '/before-case'
INSTR_STEP_AS_INSTR = '/as-instrumentation'
INSTR_STEP_AFTER_CASE = '/after-case'
INSTR_STEP_INSTR_FAIL = '/instrument-fail'
INSTR_STEP_AFTER_RUN = '/after-run'


def handlers_find_starts_with(handlers, key):
    try:
        return next(v for k, v in handlers.items() if key.startswith(k))
    except StopIteration:
        return None


class CoapAutomationHandler(threading.Thread):
    def __init__(self):
        super().__init__()
        self.q = Queue()
        self.processing_lock = threading.Lock()
        self.stop_event = threading.Event()  # used to signal termination to the threads
        self.status = AutomationStatus()

    def process(self, job):
        instrumentation_step, params = job
        test_suite = params['CODE_SUITE']
        test_group = params['CODE_TEST_GROUP']
        logging.debug('Test suite {}'.format(test_suite))
        logging.debug('Processing {}'.format(test_group))

        if str.startswith(instrumentation_step, INSTR_STEP_BEFORE_CASE):
            self.processing_lock.acquire()
            logging.debug("Acquire lock")
            logging.debug("Release lock")
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_AFTER_CASE):
            self.processing_lock.acquire()
            logging.debug("Acquire lock")
            logging.debug("Release lock")
            self.processing_lock.release()
            return

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while not self.stop_event.is_set():
            if not self.q.empty():
                item = self.q.get()
                logging.debug('Getting ' + str(item) + ' : ' + str(self.q.qsize()) + ' items in queue')
                try:
                    self.process(item)
                except Exception as e:
                    logging.error('Exception: {}'.format(str(e)))
                    self.status.errors.append(str(e))
                    self.status.verdict = 'fail'
                finally:
                    if self.processing_lock.locked():
                        self.processing_lock.release()
        return

    def post(self, instrumentation_step, params):
        # If we receive next step and we are still processing
        # previous step then we should wait for it to finish
        if self.processing_lock.locked():
            logging.debug('Automation is still processing')
            self.processing_lock.acquire(blocking=True)
            logging.debug('Post release')
            self.processing_lock.release()

        try:
            self.q.put_nowait((instrumentation_step, params))
        except Full:
            self.status.verdict = 'fail'
            self.status.errors.append('Processing queue is full')
            return False

        return True

    def get_status(self):
        s = self.status
        self.status = AutomationStatus()
        return s

    def stop(self):
        self.stop_event.set()

    def parallel(func):
        def parallel_func(*args, **kw):
            p = Process(target=func, args=args, kwargs=kw)
            p.start()
        return parallel_func

    @parallel
    def make_server(self, host, port):
        self.start()
        httpd = HTTPServer((host, port),
                           MakeInstrumentationServer(self))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.shutdown()
            return 0
