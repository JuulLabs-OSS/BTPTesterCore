import logging
import threading
from queue import Queue, Full

from defensics.automation_status import AutomationStatus
from defensics.coap_proxy import CoapProxy
from defensics.udp_server import UDPServer
from pybtp import btp
from stack.gap import BleAddress
from testcases.utils import preconditions

TESTER_ADDR = BleAddress('001bdc069e49', 0)
# TESTER_ADDR = BleAddress('001bdcf21c48', 0)
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


def test_case_setup(iut):
    iut.wait_iut_ready_event()
    preconditions(iut)


def test_case_check_health(iut):
    btp.gap_read_ctrl_info(iut)


def test_ATT_Server(iut, valid):
    test_case_setup(iut)
    btp.gap_set_conn(iut)
    btp.gap_set_gendiscov(iut)
    btp.gap_adv_ind_on(iut)


before_case_handlers = {
    'ATT.MTU-Exchange': test_ATT_Server,
}


def handlers_find_starts_with(handlers, key):
    try:
        return next(v for k, v in handlers.items() if key.startswith(k))
    except StopIteration:
        return None


class CoapAutomationHandler(threading.Thread):
    def __init__(self, proxy: CoapProxy, udp_server: UDPServer):
        super().__init__()
        self.proxy = proxy
        self.udp_server = udp_server
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
        self.udp_server.start()
        self.proxy.start()

        for data in self.udp_server.recv():
            if self.proxy.is_ready():
                try:
                    rsp = self.proxy.send(data)
                    self.udp_server.send(rsp)
                except TimeoutError:
                    pass
            else:
                raise Exception("Proxy not ready")


        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        #
        # while not self.stop_event.is_set():
        #     if not self.q.empty():
        #         item = self.q.get()
        #         logging.debug('Getting ' + str(item) + ' : ' + str(self.q.qsize()) + ' items in queue')
        #         try:
        #             self.process(item)
        #         except socket.timeout as e:
        #             logging.error('Exception: BTP Timeout')
        #             self.status.errors.append('Exception: BTP Timeout')
        #             self.status.verdict = 'fail'
        #         except AssertionError as e:
        #             logging.error('Exception: Assertion error')
        #             self.status.errors.append('Exception: Assertion error')
        #             self.status.verdict = 'fail'
        #         except TimeoutError as e:
        #             logging.error('Exception: Timeout error')
        #             self.status.errors.append('Exception: Timeout error')
        #             self.status.verdict = 'fail'
        #         except Exception as e:
        #             logging.error('Exception: {}'.format(str(e)))
        #             self.status.errors.append(str(e))
        #             self.status.verdict = 'fail'
        #         finally:
        #             if self.processing_lock.locked():
        #                 self.processing_lock.release()
        # return

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
