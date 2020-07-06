import logging
import threading

from multiprocessing import Process
from queue import Queue, Full
import asyncio
from http.server import HTTPServer
from pathlib import Path
from time import asctime
import shutil

from defensics.automation_status import AutomationStatus
from defensics.instrumentation_server import MakeInstrumentationServer
from defensics.tooling import *
from stack.gap import BleAddress
from coap_config import *
from os import devnull

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
        if btmon_enable:
            self.btmon = None
            self.btmon_process = None
            self.max_btmon_tries = 10
        self.result_path = None
        self.test_path = None
        self.serial_out = None
        self.newtmgr = None

    def process(self, job):
        instrumentation_step, params = job
        test_suite = params['CODE_SUITE']
        test_group = params['CODE_TEST_GROUP']
        logging.debug('Test suite {}'.format(test_suite))
        logging.debug('Processing {}'.format(test_group))

        if str.startswith(instrumentation_step, INSTR_STEP_BEFORE_RUN):
            self.processing_lock.acquire()
            logging.debug("Executing: before run")
            logging.debug("Acquire lock")
            # print test run info
            logging.debug('Running suite: ' + params['CODE_SUITE'])
            logging.debug('Platform version: ' + params['CODE_SUITE_PLATFORM_VERSION'])
            logging.debug('Monitor version: ' + params['CODE_MONITOR_VERSION'])
            # make folder for results
            self.result_path = Path.cwd() / asctime()
            self.result_path.mkdir(parents=True, exist_ok=True)
            # make newtmgr instance and add connection
            self.newtmgr = NewtMgr(profile_name='test', conn_type='oic_ble', connstring='"peer_name=c5"')
            self.newtmgr.make_profile()
            logging.debug("Release lock")
            # consume buffered serial data by reading it and saving to /dev/null
            self.serial_out = SerialOutput(path=devnull,
                                           newtmgr=self.newtmgr)
            self.serial_out.start()
            self.serial_out.shutdown = True
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_BEFORE_CASE):
            self.processing_lock.acquire()
            logging.debug("Executing: before case")
            # make folder for this test results
            self.newtmgr.testcase = params['CODE_TEST_CASE']
            self.test_path = self.result_path / ('#' + params['CODE_TEST_CASE'])
            self.test_path.mkdir(parents=True, exist_ok=True)
            logging.debug("Acquire lock")
            test_case = params['CODE_TEST_CASE']
            # open btmon
            if btmon_enable:
                self.btmon = BTMonitor(testcase=test_case)
                rc = self.btmon.begin()
                logging.debug(rc)
                while rc == 1:
                    logging.debug('restarting btmon')
                    self.btmon.close()
                    self.btmon = BTMonitor(testcase=test_case)

                    rc = self.btmon.begin()
                    logging.debug(rc)

            # read from serial
            self.serial_out = SerialOutput(testcase=test_case, path=self.test_path,
                                           newtmgr=self.newtmgr)
            self.serial_out.start()
            logging.debug("Release lock")
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_AS_INSTR):
            self.processing_lock.acquire()
            logging.debug("Executing: as instrumentation")
            logging.debug("Acquire lock")
            logging.debug("Release lock")
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_AFTER_CASE):
            self.processing_lock.acquire()
            logging.debug("Executing: after case")
            logging.debug("Acquire lock")
            # close btmon
            if btmon_enable:
                self.btmon.close()
                self.btmon = None
            # end reading from serial
            self.serial_out.shutdown = True
            self.serial_out.join()
            # copy log files to results folder
            if btmon_enable:
                snoop_file = Path.cwd() / (params['CODE_TEST_CASE'] + '.snoop')
                shutil.copy(snoop_file, self.test_path)
                Path.unlink(snoop_file)
            serial_out_file = Path.cwd() / (params['CODE_TEST_CASE'] + '.txt')
            shutil.copy(serial_out_file, self.test_path)
            # coredumps are not copied, as newtmgr is run as sudo and coredumps are protected
            Path.unlink(serial_out_file)
            logging.debug("Release lock")
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_INSTR_FAIL):
            self.processing_lock.acquire()
            logging.debug("Acquire lock")
            logging.debug("Executing: fail")
            logging.debug("Release lock")
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_AFTER_RUN):
            self.processing_lock.acquire()
            logging.debug("Acquire lock")
            logging.debug("Executing: after run")
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
