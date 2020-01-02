import asyncio
import logging
import socket
import threading
from queue import Queue, Full

from defensics.automation_status import AutomationStatus
from pybtp import btp, defs
from pybtp.types import IOCap, BTPErrorInvalidStatus
from pybtp.utils import wait_futures
from stack.gap import BleAddress
from stack.gatt import GattDB
from testcases.utils import preconditions, EV_TIMEOUT, find_adv_by_addr

# TESTER_ADDR = BleAddress('001bdc069e49', 0)
# TESTER_ADDR = BleAddress('001bdcf21c48', 0)
TESTER_ADDR = BleAddress('001BDC08E676', 0)
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


def test_case_teardown(iut):
    pass


def test_ATT_Server(iut, valid):
    btp.gap_set_conn(iut)
    btp.gap_set_gendiscov(iut)
    btp.gap_adv_ind_on(iut)


def test_ATT_Client_Exchange_MTU(iut, valid):
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)
    btp.gattc_exchange_mtu(iut, TESTER_ADDR)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    try:
        btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                          defs.GATT_EXCHANGE_MTU)
    except BTPErrorInvalidStatus:
        pass


def test_ATT_Client_Discover_Primary_Services(iut, valid):
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_disc_prim_svcs(iut, TESTER_ADDR)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    try:
        btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                          defs.GATT_DISC_PRIM_SVCS)
    except BTPErrorInvalidStatus:
        pass

    try:
        # In some test cases Defensics won't disconnect
        # so we have to try to disconnect ourselves
        btp.gap_disconn(iut, TESTER_ADDR)
    except BTPErrorInvalidStatus:
        pass


def test_ATT_Client_Discover_Service_by_uuid(iut, valid):
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_disc_prim_uuid(iut, TESTER_ADDR, TESTER_SERVICE_UUID)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    try:
        btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                          defs.GATT_DISC_PRIM_UUID)
    except BTPErrorInvalidStatus:
        pass


def test_ATT_Client_Discover_All_Characteristics(iut, valid):
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_disc_all_chrc(iut, TESTER_ADDR, start_hdl=1, stop_hdl=0xffff)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    try:
        btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                          defs.GATT_DISC_ALL_CHRC)
    except BTPErrorInvalidStatus:
        pass


def test_ATT_Client_Discover_Characteristic_Descriptors(iut, valid):
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
        try:
            btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                              defs.GATT_DISC_ALL_DESC)
        except BTPErrorInvalidStatus:
            pass


def test_ATT_Client_Read_Attribute_Value(iut, valid):
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_read(iut, TESTER_ADDR, TESTER_READ_HDL)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    try:
        btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                          defs.GATT_READ)
    except BTPErrorInvalidStatus:
        pass


def test_ATT_Client_Read_Long_Attribute_Value(iut, valid):
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_read_long(iut, TESTER_ADDR, TESTER_READ_HDL, 0)
    tuple_hdr, tuple_data = iut.btp_worker.read()
    try:
        btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                          defs.GATT_READ_LONG)
    except BTPErrorInvalidStatus:
        pass

    try:
        # In some test cases Defensics won't disconnect
        # so we have to try to disconnect ourselves
        btp.gap_disconn(iut, TESTER_ADDR)
    except BTPErrorInvalidStatus:
        pass


def test_ATT_Client_Write_Attribute_Value(iut, valid):
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    btp.gattc_write(iut, TESTER_ADDR, TESTER_WRITE_HDL, '00')
    tuple_hdr, tuple_data = iut.btp_worker.read()
    try:
        btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                          defs.GATT_WRITE)
    except BTPErrorInvalidStatus:
        pass


def test_SMP_Server_SC_Just_Works(iut, valid):
    btp.gap_set_io_cap(iut, IOCap.keyboard_display)
    btp.gap_set_conn(iut)
    btp.gap_set_gendiscov(iut)
    btp.gap_adv_ind_on(iut)


def test_SMP_Server_SC_Numeric_Comparison(iut, valid):
    btp.gap_set_io_cap(iut, IOCap.keyboard_display)
    btp.gap_set_conn(iut)
    btp.gap_set_gendiscov(iut)
    btp.gap_adv_ind_on(iut)

    future = btp.gap_passkey_confirm_req_ev(iut)
    try:
        wait_futures([future], timeout=EV_TIMEOUT)
        results = future.result()
        pk_iut = results[1]
        assert (pk_iut is not None)
        btp.gap_passkey_confirm(iut, TESTER_ADDR, 1)
    except (TimeoutError, BTPErrorInvalidStatus) as e:
        if valid:
            raise e


def test_SMP_Server_SC_Passkey_Entry(iut, valid):
    btp.gap_set_io_cap(iut, IOCap.keyboard_display)
    btp.gap_set_conn(iut)
    btp.gap_set_gendiscov(iut)
    btp.gap_adv_ind_on(iut)

    future = btp.gap_passkey_entry_req_ev(iut)
    try:
        wait_futures([future], timeout=EV_TIMEOUT)
        btp.gap_passkey_entry_rsp(iut, TESTER_ADDR, TESTER_PASSKEY)
    except (TimeoutError, BTPErrorInvalidStatus) as e:
        if valid:
            raise e


def test_SMP_Client_SC_Just_Works(iut, valid):
    btp.gap_set_io_cap(iut, IOCap.keyboard_display)
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)


def test_SMP_Client_SC_Numeric_Comparison(iut, valid):
    btp.gap_set_io_cap(iut, IOCap.keyboard_display)
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    future = btp.gap_passkey_confirm_req_ev(iut)
    try:
        wait_futures([future], timeout=EV_TIMEOUT)
        results = future.result()
        pk_iut = results[1]
        assert (pk_iut is not None)
        btp.gap_passkey_confirm(iut, TESTER_ADDR, 1)
    except (TimeoutError, BTPErrorInvalidStatus) as e:
        if valid:
            raise e


def test_SMP_Client_SC_Passkey_Entry(iut, valid):
    btp.gap_set_io_cap(iut, IOCap.keyboard_display)
    btp.gap_conn(iut, TESTER_ADDR)
    btp.gap_wait_for_connection(iut)

    future = btp.gap_passkey_entry_req_ev(iut)
    try:
        wait_futures([future], timeout=EV_TIMEOUT)
        btp.gap_passkey_entry_rsp(iut, TESTER_ADDR, TESTER_PASSKEY)
    except (TimeoutError, BTPErrorInvalidStatus) as e:
        if valid:
            raise e


def test_Advertising_Data(iut, valid):
    def verify_f(args):
        return find_adv_by_addr(args, TESTER_ADDR)

    btp.gap_start_discov(iut)
    future = btp.gap_device_found_ev(iut, verify_f)
    try:
        wait_futures([future], timeout=5)
        btp.gap_stop_discov(iut)
        found = future.result()
        assert found
    except TimeoutError as e:
        btp.gap_stop_discov(iut)
        if valid:
            raise e


before_case_handlers = {
    'ATT.MTU-exchange': test_ATT_Client_Exchange_MTU,
    'ATT.Discover-primary-services': test_ATT_Client_Discover_Primary_Services,
    'ATT.Discover-service-by-uuid': test_ATT_Client_Discover_Service_by_uuid,
    'ATT.Characteristic-Discovery.discover-all-characteristics': test_ATT_Client_Discover_All_Characteristics,
    'ATT.Characteristic-Discovery.discover-characteristic-descriptors': test_ATT_Client_Discover_Characteristic_Descriptors,
    'ATT.Read-attribute-value': test_ATT_Client_Read_Attribute_Value,
    'ATT.Read-long-attribute-value': test_ATT_Client_Read_Long_Attribute_Value,
    'ATT.Write-attribute-value': test_ATT_Client_Write_Attribute_Value,
    'ATT.MTU-Exchange': test_ATT_Server,
    'ATT.Primary-Service-Discovery': test_ATT_Server,
    'ATT.Relationship-Discovery': test_ATT_Server,
    'ATT.Characteristic-Discovery.Discover-All-Characteristics-Of-A-Service': test_ATT_Server,
    'ATT.Characteristic-Value-Read': test_ATT_Server,
    'ATT.Characteristic-Value-Write': test_ATT_Server,
    'SMP.SMP-SC-just-works': test_SMP_Server_SC_Just_Works,
    'SMP.SMP-SC-numeric-comparison': test_SMP_Server_SC_Numeric_Comparison,
    'SMP.SMP-SC-passkey-entry': test_SMP_Server_SC_Passkey_Entry,
    'SMPC.SMP-SC-just-works': test_SMP_Client_SC_Just_Works,
    'SMPC.SMP-SC-numeric-comparison': test_SMP_Client_SC_Numeric_Comparison,
    'SMPC.SMP-SC-passkey-entry': test_SMP_Client_SC_Passkey_Entry,
    'Advertising-Data': test_Advertising_Data,
}


def handlers_find_starts_with(handlers, key):
    try:
        return next(v for k, v in handlers.items() if key.startswith(k))
    except StopIteration:
        return None


class BTPAutomationHandler(threading.Thread):
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

        test_suite = params['CODE_SUITE']
        logging.debug('Test suite {}'.format(test_suite))

        # This workaround is needed because Defensics has
        # the same test group names for Client and Server
        if 'smpc' in test_suite:
            test_group = str.replace(test_group, 'SMP.', 'SMPC.')

        logging.debug('Processing {}'.format(test_group))

        if str.startswith(instrumentation_step, INSTR_STEP_BEFORE_CASE):

            # Find a test handler by test group name
            hdl = handlers_find_starts_with(before_case_handlers, test_group)
            if hdl is None:
                raise Exception("Unsupported test group: ", test_group)

            # valid = 'valid' in test_group
            # Assume all test cases are invalid
            valid = False

            self.processing_lock.acquire()
            logging.debug("Acquire lock")
            test_case_setup(self.iut)
            # Execute test handler
            hdl(self.iut, valid)
            test_case_teardown(self.iut)
            logging.debug("Release lock")
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_AFTER_CASE):
            self.processing_lock.acquire()
            logging.debug("Acquire lock")
            # Check if IUT is ok
            test_case_check_health(self.iut)
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
