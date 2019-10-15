import asyncio
import json
import logging
import socket
import threading
from queue import Queue, Full

from pybtp import btp, defs
from pybtp.types import BTPError
from stack.gap import BleAddress
from stack.gatt import GattDB, GattValue
from testcases.utils import preconditions

TESTER_ADDR = BleAddress('00:1B:DC:F2:1C:48', 0)
TESTER_READ_HDL = '0x0003'
TESTER_WRITE_HDL = '0x0005'
TESTER_SERVICE_UUID = '180F'

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


def test_ATT_Client_Exchange_MTU(iut):
    test_case_setup(iut)
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)
    btp.gattc_exchange_mtu(iut, TESTER_ADDR)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                      defs.GATT_EXCHANGE_MTU, ignore_status=True)

    test_case_check_health(iut)


def test_ATT_Client_Discover_Primary_Services(iut):
    test_case_setup(iut)
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_disc_prim_svcs(iut, TESTER_ADDR)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                      defs.GATT_DISC_PRIM_SVCS, ignore_status=True)

    test_case_check_health(iut)


def test_ATT_Client_Discover_Service_by_uuid(iut):
    test_case_setup(iut)
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_disc_prim_uuid(iut, TESTER_ADDR, TESTER_SERVICE_UUID)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                      defs.GATT_DISC_PRIM_UUID, ignore_status=True)

    test_case_check_health(iut)


def test_ATT_Client_Discover_All_Characteristics(iut):
    test_case_setup(iut)
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_disc_all_chrc(iut, TESTER_ADDR, start_hdl=1, stop_hdl=0xffff)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                      defs.GATT_DISC_ALL_CHRC, ignore_status=True)

    test_case_check_health(iut)


def test_ATT_Client_Discover_Characteristic_Descriptors(iut):
    test_case_setup(iut)
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    db = GattDB()
    btp.gattc_disc_prim_svcs(iut, TESTER_ADDR)
    btp.gattc_disc_prim_svcs_rsp(iut, db)

    for svc in db.get_services():
        start, end = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(iut, TESTER_ADDR, start, end)
        btp.gattc_disc_all_chrc_rsp(iut, db)

    for char in db.get_characteristics():
        start_hdl = char.value_handle + 1
        end_hdl = db.find_characteristic_end(char.handle)
        if not end_hdl:
            # There are no descriptors there so continue
            continue

        # Defensics expects to receive a Request with start handle == end handle
        if end_hdl == 0xffff:
            end_hdl = start_hdl

        btp.gattc_disc_all_desc(iut, TESTER_ADDR, start_hdl, end_hdl)
        tuple_hdr, tuple_data = iut.btp_worker.read()
        btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                          defs.GATT_DISC_ALL_DESC, ignore_status=True)

    test_case_check_health(iut)


def test_ATT_Client_Read_Attribute_Value(iut):
    test_case_setup(iut)
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_read(iut, TESTER_ADDR, TESTER_READ_HDL)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                      defs.GATT_READ, ignore_status=True)

    test_case_check_health(iut)


def test_ATT_Client_Read_Long_Attribute_Value(iut):
    test_case_setup(iut)
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_read_long(iut, TESTER_ADDR, TESTER_READ_HDL, 0)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                      defs.GATT_READ_LONG, ignore_status=True)

    test_case_check_health(iut)


def test_ATT_Client_Write_Attribute_Value(iut):
    test_case_setup(iut)
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_write(iut, TESTER_ADDR, TESTER_WRITE_HDL, '00')
    tuple_hdr, tuple_data = iut.btp_worker.read()
    btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                      defs.GATT_WRITE, ignore_status=True)

    test_case_check_health(iut)


before_case_handlers = {
    'ATT.MTU-exchange': test_ATT_Client_Exchange_MTU,
    'ATT.Discover-primary-services': test_ATT_Client_Discover_Primary_Services,
    'ATT.Discover-service-by-uuid': test_ATT_Client_Discover_Service_by_uuid,
    'ATT.Characteristic-Discovery.discover-all-characteristics': test_ATT_Client_Discover_All_Characteristics,
    'ATT.Characteristic-Discovery.discover-characteristic-descriptors': test_ATT_Client_Discover_Characteristic_Descriptors,
    'ATT.Read-attribute-value': test_ATT_Client_Read_Attribute_Value,
    'ATT.Read-long-attribute-value': test_ATT_Client_Read_Long_Attribute_Value,
    'ATT.Write-attribute-value': test_ATT_Client_Write_Attribute_Value,
}


def handlers_find_starts_with(handlers, key):
    try:
        return next(v for k, v in handlers.items() if key.startswith(k))
    except StopIteration:
        return None


class AutomationStatus:
    def __init__(self):
        self.status = 0
        self.errors = []
        self.verdict = ''

    def to_json(self):
        return json.dumps({
            'status': self.status,
            'errors': self.errors,
            'verdict': self.verdict,
        })


class AutomationHandler(threading.Thread):
    def __init__(self, iut):
        super().__init__()
        if iut is None:
            raise Exception("IUT1 is None")
        self.iut = iut
        self.q = Queue()
        self.processing_lock = threading.Lock()
        self.stop_event = threading.Event()  # used to signal termination to the threads
        self.status = AutomationStatus()

    def process(self, job):
        instrumentation_step, params = job

        test_group = params['CODE_TEST_GROUP']

        if str.startswith(instrumentation_step, INSTR_STEP_BEFORE_CASE):

            # Find a test handler by test group name
            hdl = handlers_find_starts_with(before_case_handlers, test_group)
            if hdl is None:
                raise Exception("Unsupported test group: ", test_group)

            self.processing_lock.acquire()
            # Execute test handler
            hdl(self.iut)
            self.processing_lock.release()
            return

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while not self.stop_event.set():
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
