import asyncio
import logging
import socket
import threading
from queue import Queue, Full

from defensics.automation_status import AutomationStatus
from defensics.testcase_handler import TestCaseHandler

INSTR_STEP_BEFORE_RUN = '/before-run'
INSTR_STEP_BEFORE_CASE = '/before-case'
INSTR_STEP_AS_INSTR = '/as-instrumentation'
INSTR_STEP_AFTER_CASE = '/after-case'
INSTR_STEP_INSTR_FAIL = '/instrument-fail'
INSTR_STEP_AFTER_RUN = '/after-run'


class BTPAutomationHandler(threading.Thread):
    def __init__(self, iut, tester_config):
        super().__init__()
        self.iut = iut
        self.tester_config = tester_config
        self.test_case_handler = TestCaseHandler(self.tester_config)
        self.q = Queue()
        self.processing_lock = threading.Lock()
        self.stop_event = threading.Event()  # used to signal termination to the threads
        self.status = AutomationStatus()

    def process(self, job):
        instrumentation_step, params = job

        test_group = params['CODE_TEST_GROUP']
        test_suite = params['CODE_SUITE']
        logging.debug('Test suite {}'.format(test_suite))

        # This workaround is needed because Defensics has
        # the same test group names for Client and Server
        if 'smpc' in test_suite:
            test_group = str.replace(test_group, 'SMP.', 'SMPC.')

        logging.debug('Processing {}'.format(test_group))

        if str.startswith(instrumentation_step, INSTR_STEP_BEFORE_CASE):

            # Find a test handler by test group name
            hdl = self.test_case_handler.get_before_case_handler(test_group)
            if hdl is None:
                raise Exception("Unsupported test group: ", test_group)

            # valid = 'valid' in test_group
            # Assume all test cases are invalid
            valid = False

            self.processing_lock.acquire()
            logging.debug("Acquire lock")
            self.test_case_handler.test_case_setup(self.iut)
            # Execute test handler
            hdl(self.test_case_handler, self.iut, valid)
            self.test_case_handler.test_case_teardown(self.iut)
            logging.debug("Release lock")
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_AFTER_CASE):
            self.processing_lock.acquire()
            logging.debug("Acquire lock")
            # Check if IUT is ok
            self.test_case_handler.test_case_check_health(self.iut)
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
                except socket.timeout as e:
                    logging.error('Exception: BTP Timeout')
                    self.status.errors.append('Exception: BTP Timeout')
                    self.status.verdict = 'fail'
                except AssertionError as e:
                    logging.error('Exception: Assertion error')
                    self.status.errors.append('Exception: Assertion error')
                    self.status.verdict = 'fail'
                except TimeoutError as e:
                    logging.error('Exception: Timeout error')
                    self.status.errors.append('Exception: Timeout error')
                    self.status.verdict = 'fail'
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
