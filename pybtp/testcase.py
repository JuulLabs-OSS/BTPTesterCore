import logging
import os
import time
import unittest

from pybtp import btp
from pybtp.btp import parse_ad, ad_find_uuid16
from pybtp.types import IOCap, AdType, UUID, PTS_DB, Prop, Perm
from pybtp.utils import wait_futures
from stack.gap import BleAddress
from stack.gatt import GattDB, GattValue

EV_TIMEOUT = 20


def preconditions(iutctl):
    btp.core_reg_svc_gap(iutctl)
    btp.core_reg_svc_gatt(iutctl)
    iutctl.stack.gap_init()
    iutctl.stack.gatt_init()
    btp.gap_read_ctrl_info(iutctl)


def find_adv_by_uuid(args, uuid):
    le_adv = args
    logging.debug("matching %r", le_adv)
    ad = parse_ad(le_adv.eir)
    uuids = ad_find_uuid16(ad)

    return uuid in uuids


def verify_conn_params(args, addr: BleAddress,
                       conn_itvl_min, conn_itvl_max,
                       conn_latency, supervision_timeout):
    params = args[1]
    return verify_address(args, addr) and \
           (params.conn_itvl >= conn_itvl_min) and \
           (params.conn_itvl <= conn_itvl_max) and \
           (params.conn_latency == conn_latency) and \
           (params.supervision_timeout == supervision_timeout)


def verify_address(args, addr: BleAddress):
    peer_addr = args[0]
    return peer_addr == addr


def verify_value_changed_ev(args, handle, value):
    return args[0] == handle and args[1] == value


def verify_notification_ev(args, addr: BleAddress, type, handle, data):
    logging.debug("%r %r %r %r %r", args, addr, type, handle, data)
    return args[0] == addr and args[1] == type and \
           args[2] == handle and args[3] == data


def connection_procedure(testcase, central, peripheral):
    btp.gap_set_conn(peripheral)
    btp.gap_set_gendiscov(peripheral)

    uuid = os.urandom(2)
    btp.gap_adv_ind_on(peripheral, ad=[(AdType.uuid16_some, uuid)])

    def verify_f(args): return find_adv_by_uuid(args,
                                                btp.btp2uuid(len(uuid), uuid))

    btp.gap_start_discov(central)
    future = btp.gap_device_found_ev(central, verify_f)
    wait_futures([future], timeout=EV_TIMEOUT)
    btp.gap_stop_discov(central)

    found = future.result()

    testcase.assertIsNotNone(found)
    peripheral.stack.gap.iut_addr_set(found.addr)

    btp.gap_conn(central, peripheral.stack.gap.iut_addr_get())

    def verify_central(args): return verify_address(args, found.addr)

    future_central = btp.gap_connected_ev(central, verify_central)
    future_peripheral = btp.gap_connected_ev(peripheral)

    wait_futures([future_central, future_peripheral], timeout=EV_TIMEOUT)

    testcase.assertTrue(central.stack.gap.is_connected())
    testcase.assertTrue(peripheral.stack.gap.is_connected())


def disconnection_procedure(testcase, central, peripheral):
    periph_addr = peripheral.stack.gap.iut_addr_get()

    def verify_central(args):
        return verify_address(args, periph_addr)

    future_central = btp.gap_disconnected_ev(central, verify_central)
    future_peripheral = btp.gap_disconnected_ev(peripheral)

    btp.gap_disconn(central, peripheral.stack.gap.iut_addr_get())

    wait_futures([future_central, future_peripheral], timeout=EV_TIMEOUT)

    testcase.assertFalse(peripheral.stack.gap.is_connected())
    testcase.assertFalse(central.stack.gap.is_connected())


class BTPTestCase(unittest.TestCase):
    def __init__(self, testname, iut, lt):
        super(__class__, self).__init__(testname)

        if iut is None:
            raise Exception("IUT is None")

        if lt is None:
            raise Exception("LT is None")

        self.iut = iut
        self.lt = lt

    @classmethod
    def init_testcases(cls, iut, lt):
        testcases = []
        ldr = unittest.TestLoader()
        for testname in ldr.getTestCaseNames(cls):
            testcases.append(cls(testname, iut, lt))
        return testcases

    def setUp(self):
        self.iut.start()
        self.iut.wait_iut_ready_event()
        self.lt.start()
        self.lt.wait_iut_ready_event()

    def tearDown(self):
        self.iut.stop()
        self.lt.stop()


class BTPTestCaseLT2(unittest.TestCase):
    def __init__(self, testname, iut, lt1, lt2):
        super(__class__, self).__init__(testname)

        if iut is None:
            raise Exception("IUT is None")

        if lt1 is None:
            raise Exception("LT1 is None")

        if lt2 is None:
            raise Exception("LT2 is None")

        self.iut = iut
        self.lt1 = lt1
        self.lt2 = lt2

    @classmethod
    def init_testcases(cls, iut, lt1, lt2):
        testcases = []
        ldr = unittest.TestLoader()
        for testname in ldr.getTestCaseNames(cls):
            testcases.append(cls(testname, iut, lt1, lt2))
        return testcases

    def setUp(self):
        self.iut.start()
        self.iut.wait_iut_ready_event()
        self.lt1.start()
        self.lt1.wait_iut_ready_event()
        self.lt2.start()
        self.lt2.wait_iut_ready_event()

    def tearDown(self):
        self.iut.stop()
        self.lt1.stop()
        self.lt2.stop()


class GAPTestCase(BTPTestCase):
    def __init__(self, testname, iut, lt):
        super(__class__, self).__init__(testname, iut, lt)

    def setUp(self):
        super(__class__, self).setUp()
        preconditions(self.iut)
        preconditions(self.lt)

    def tearDown(self):
        super(__class__, self).tearDown()

    def test_scan(self):
        btp.gap_set_conn(self.lt)
        btp.gap_set_gendiscov(self.lt)
        btp.gap_adv_ind_on(self.lt,
                           ad=[(AdType.name_full,
                                self.lt.stack.gap.name.encode())])

        btp.gap_start_discov(self.iut)
        time.sleep(5)
        btp.gap_stop_discov(self.iut)
        found = btp.check_discov_results_by_name(self.iut,
                                                 self.lt.stack.gap.name,
                                                 self.lt.stack.gap.name_short)
        self.assertIsNotNone(found)

    def test_advertising(self):
        connection_procedure(self, central=self.lt, peripheral=self.iut)
        disconnection_procedure(self, central=self.lt, peripheral=self.iut)

    def test_connection(self):
        connection_procedure(self, central=self.iut, peripheral=self.lt)
        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_directed_adv(self):
        connection_procedure(self, central=self.lt, peripheral=self.iut)

        iut_addr = self.iut.stack.gap.iut_addr_get()
        lt_addr = self.lt.stack.gap.iut_addr_get()

        def verify_iut(args):
            return verify_address(args, lt_addr)

        def verify_lt(args):
            return verify_address(args, iut_addr)

        future_iut = btp.gap_sec_level_changed_ev(self.iut, verify_iut)
        future_lt = btp.gap_sec_level_changed_ev(self.lt, verify_lt)

        btp.gap_pair(self.iut, self.lt.stack.gap.iut_addr_get())

        wait_futures([future_iut, future_lt], timeout=EV_TIMEOUT)

        disconnection_procedure(self, central=self.lt, peripheral=self.iut)

        btp.gap_start_direct_adv(self.iut, self.lt.stack.gap.iut_addr_get())

        def verify_central(args):
            return verify_address(args, self.iut.stack.gap.iut_addr_get())

        future_central = btp.gap_connected_ev(self.lt, verify_central)
        future_peripheral = btp.gap_connected_ev(self.iut)

        btp.gap_conn(self.lt, self.iut.stack.gap.iut_addr_get())

        wait_futures([future_central, future_peripheral], timeout=EV_TIMEOUT)

        self.assertTrue(self.lt.stack.gap.is_connected())
        self.assertTrue(self.iut.stack.gap.is_connected())

        disconnection_procedure(self, central=self.lt, peripheral=self.iut)

    def test_connection_parameter_update_master(self):
        connection_procedure(self, central=self.iut, peripheral=self.lt)

        conn_params = self.iut.stack.gap.get_conn_params()
        iut_addr = self.iut.stack.gap.iut_addr_get()
        lt_addr = self.lt.stack.gap.iut_addr_get()

        conn_itvl_min, conn_itvl_max, latency, supervision_timeout = (
            conn_params.conn_itvl,
            conn_params.conn_itvl,
            conn_params.conn_latency + 2,
            conn_params.supervision_timeout)

        btp.gap_conn_param_update(self.iut,
                                  self.lt.stack.gap.iut_addr_get(),
                                  conn_itvl_min, conn_itvl_max, latency,
                                  supervision_timeout)

        def verify_iut(args):
            return verify_conn_params(args, lt_addr, conn_itvl_min,
                                      conn_itvl_max, latency,
                                      supervision_timeout)

        def verify_lt(args):
            return verify_conn_params(args, iut_addr, conn_itvl_min,
                                      conn_itvl_max, latency,
                                      supervision_timeout)

        wait_futures([btp.gap_conn_param_update_ev(self.iut, verify_iut),
                      btp.gap_conn_param_update_ev(self.lt, verify_lt)],
                     timeout=EV_TIMEOUT)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_connection_parameter_update_slave(self):
        connection_procedure(self, central=self.iut, peripheral=self.lt)

        conn_params = self.iut.stack.gap.get_conn_params()
        iut_addr = self.iut.stack.gap.iut_addr_get()
        lt_addr = self.lt.stack.gap.iut_addr_get()

        conn_itvl_min, conn_itvl_max, latency, supervision_timeout = (
            conn_params.conn_itvl,
            conn_params.conn_itvl,
            conn_params.conn_latency + 2,
            conn_params.supervision_timeout)

        btp.gap_conn_param_update(self.lt,
                                  self.iut.stack.gap.iut_addr_get(),
                                  conn_itvl_min, conn_itvl_max, latency,
                                  supervision_timeout)

        def verify_iut(args):
            return verify_conn_params(args, lt_addr, conn_itvl_min,
                                      conn_itvl_max, latency,
                                      supervision_timeout)

        def verify_lt(args):
            return verify_conn_params(args, iut_addr, conn_itvl_min,
                                      conn_itvl_max, latency,
                                      supervision_timeout)

        wait_futures([btp.gap_conn_param_update_ev(self.iut, verify_iut),
                      btp.gap_conn_param_update_ev(self.lt, verify_lt)],
                     timeout=EV_TIMEOUT)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_pairing_jw(self):
        btp.gap_set_io_cap(self.lt, IOCap.no_input_output)
        connection_procedure(self, central=self.iut, peripheral=self.lt)

        iut_addr = self.iut.stack.gap.iut_addr_get()
        lt_addr = self.lt.stack.gap.iut_addr_get()

        def verify_iut(args):
            return verify_address(args, lt_addr)

        def verify_lt(args):
            return verify_address(args, iut_addr)

        future_iut = btp.gap_sec_level_changed_ev(self.iut, verify_iut)
        future_lt = btp.gap_sec_level_changed_ev(self.lt, verify_lt)

        btp.gap_pair(self.iut, self.lt.stack.gap.iut_addr_get())

        wait_futures([future_iut, future_lt], timeout=EV_TIMEOUT)

        _, level = future_iut.result()
        self.assertEqual(level, 1)

        _, level = future_lt.result()
        self.assertEqual(level, 1)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_pairing_numcmp(self):
        btp.gap_set_io_cap(self.iut, IOCap.display_yesno)
        btp.gap_set_io_cap(self.lt, IOCap.display_yesno)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gap_pair(self.iut, self.lt.stack.gap.iut_addr_get())

        iut_addr = self.iut.stack.gap.iut_addr_get()
        lt_addr = self.lt.stack.gap.iut_addr_get()

        def verify_master(args): return verify_address(args, lt_addr)

        def verify_slave(args): return verify_address(args, iut_addr)

        future_master = btp.gap_passkey_confirm_req_ev(self.iut, verify_master)
        future_slave = btp.gap_passkey_confirm_req_ev(self.lt, verify_slave)

        wait_futures([future_master, future_slave], timeout=EV_TIMEOUT)

        results_master = future_master.result()
        results_slave = future_slave.result()

        pk_iut = results_master[1]
        self.assertIsNotNone(pk_iut)
        pk_lt = results_slave[1]
        self.assertIsNotNone(pk_lt)
        self.assertEqual(pk_iut, pk_lt)

        btp.gap_passkey_confirm(self.iut,
                                self.lt.stack.gap.iut_addr_get(), 1)

        btp.gap_passkey_confirm(self.lt,
                                self.iut.stack.gap.iut_addr_get(), 1)

        future_master = btp.gap_sec_level_changed_ev(self.iut, verify_master)
        future_slave = btp.gap_sec_level_changed_ev(self.lt, verify_slave)

        wait_futures([future_master, future_slave], timeout=EV_TIMEOUT)

        _, level = future_master.result()
        self.assertEqual(level, 3)

        _, level = future_slave.result()
        self.assertEqual(level, 3)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_pairing_input(self):
        btp.gap_set_io_cap(self.iut, IOCap.keyboard_only)
        btp.gap_set_io_cap(self.lt, IOCap.display_only)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gap_pair(self.iut,
                     self.lt.stack.gap.iut_addr_get())

        iut_addr = self.iut.stack.gap.iut_addr_get()
        lt_addr = self.lt.stack.gap.iut_addr_get()

        def verify_master(args): return verify_address(args, lt_addr)

        def verify_slave(args): return verify_address(args, iut_addr)

        future_slave = btp.gap_passkey_disp_ev(self.lt, verify_slave)
        future_master = btp.gap_passkey_entry_req_ev(self.iut, verify_master)

        wait_futures([future_master, future_slave], timeout=EV_TIMEOUT)
        results_slave = future_slave.result()
        pk_lt = results_slave[1]
        self.assertIsNotNone(pk_lt)

        btp.gap_passkey_entry_rsp(self.iut, lt_addr, pk_lt)

        future_master = btp.gap_sec_level_changed_ev(self.iut, verify_master)
        future_slave = btp.gap_sec_level_changed_ev(self.lt, verify_slave)

        wait_futures([future_master, future_slave], timeout=EV_TIMEOUT)

        _, level = future_master.result()
        self.assertEqual(level, 3)

        _, level = future_slave.result()
        self.assertEqual(level, 3)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_discover_primary_svcs(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        btp.gatts_add_svc(self.lt, 0, PTS_DB.INC_SVC)
        btp.gatts_start_server(self.lt)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_prim_svcs(self.iut,
                                 self.lt.stack.gap.iut_addr_get())

        db = GattDB()
        btp.gattc_disc_prim_svcs_rsp(self.iut, db)

        self.assertIsNotNone(db.find_svc_by_uuid(PTS_DB.SVC))
        self.assertIsNotNone(db.find_svc_by_uuid(PTS_DB.INC_SVC))

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_discover_primary_uuid(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        btp.gatts_start_server(self.lt)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_prim_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut, db)

        self.assertIsNotNone(db.find_svc_by_uuid(PTS_DB.SVC))

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_find_incl_svcs(self):
        inc_id = btp.gatts_add_svc(self.lt, 0, PTS_DB.INC_SVC)
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        btp.gatts_add_inc_svc(self.lt, inc_id)
        btp.gatts_start_server(self.lt)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_prim_svcs(self.iut,
                                 self.lt.stack.gap.iut_addr_get())

        db = GattDB()
        btp.gattc_disc_prim_svcs_rsp(self.iut, db)

        for svc in db.get_services():
            start_hdl, end_hdl = svc.handle, svc.end_hdl

            btp.gattc_find_included(self.iut,
                                    self.lt.stack.gap.iut_addr_get(),
                                    start_hdl, end_hdl)

            btp.gattc_find_included_rsp(self.iut, db)

        db.print_db()

        self.assertIsNotNone(db.find_inc_svc_by_uuid(PTS_DB.INC_SVC))

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_discover_all_chrcs(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        btp.gatts_add_char(self.lt, 0, Prop.read | Prop.write,
                           Perm.read | Perm.write,
                           PTS_DB.CHR_READ_WRITE)
        btp.gatts_start_server(self.lt)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_prim_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_discover_chrc_uuid(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        btp.gatts_add_char(self.lt, 0, Prop.read | Prop.write,
                           Perm.read | Perm.write,
                           PTS_DB.CHR_READ_WRITE)
        btp.gatts_start_server(self.lt)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)

        self.assertIsNotNone(chr)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_discover_all_descs(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        btp.gatts_add_char(self.lt, 0, Prop.read | Prop.write,
                           Perm.read | Perm.write,
                           PTS_DB.CHR_READ_WRITE)
        btp.gatts_add_desc(self.lt, 0, Perm.read | Perm.write,
                           PTS_DB.DSC_READ_WRITE)
        btp.gatts_start_server(self.lt)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_prim_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)

        btp.gattc_disc_all_desc_rsp(self.iut, db)

        db.print_db()

        dsc = db.find_dsc_by_uuid(PTS_DB.DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_read_characteristic(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        char_id = btp.gatts_add_char(self.lt, 0, Prop.read | Prop.write,
                                     Perm.read | Perm.write,
                                     PTS_DB.CHR_READ_WRITE)
        btp.gatts_start_server(self.lt)

        value = "123456"
        btp.gatts_set_val(self.lt, char_id, value)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        btp.gattc_read(self.iut,
                       self.lt.stack.gap.iut_addr_get(),
                       chr.value_handle)

        val = GattValue()
        btp.gattc_read_rsp(self.iut, val)

        self.assertEqual(val.att_rsp, "No error")
        self.assertEqual(val.value, value)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_read_descriptor(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        btp.gatts_add_char(self.lt, 0, Prop.read | Prop.write,
                           Perm.read | Perm.write,
                           PTS_DB.CHR_READ_WRITE)
        desc_id = btp.gatts_add_desc(self.lt, 0, Perm.read | Perm.write,
                                     PTS_DB.DSC_READ_WRITE)
        btp.gatts_start_server(self.lt)

        value = "123456"
        btp.gatts_set_val(self.lt, desc_id, value)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_prim_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)

        btp.gattc_disc_all_desc_rsp(self.iut, db)

        db.print_db()

        dsc = db.find_dsc_by_uuid(PTS_DB.DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        btp.gattc_read(self.iut,
                       self.lt.stack.gap.iut_addr_get(),
                       dsc.handle)

        val = GattValue()
        btp.gattc_read_rsp(self.iut, val)

        self.assertEqual(val.att_rsp, "No error")
        self.assertEqual(val.value, value)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_read_long_characteristic(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        char_id = btp.gatts_add_char(self.lt, 0, Prop.read | Prop.write,
                                     Perm.read | Perm.write,
                                     PTS_DB.CHR_READ_WRITE)
        btp.gatts_start_server(self.lt)

        value = "FF" * 280
        btp.gatts_set_val(self.lt, char_id, value)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        btp.gattc_read_long(self.iut,
                            self.lt.stack.gap.iut_addr_get(),
                            chr.value_handle, 0)

        val = GattValue()
        btp.gattc_read_long_rsp(self.iut, val)

        self.assertEqual(val.att_rsp, "No error")
        self.assertEqual(val.value, value)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_read_long_descriptor(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        btp.gatts_add_char(self.lt, 0, Prop.read | Prop.write,
                           Perm.read | Perm.write,
                           PTS_DB.CHR_READ_WRITE)
        desc_id = btp.gatts_add_desc(self.lt, 0, Perm.read | Perm.write,
                                     PTS_DB.DSC_READ_WRITE)
        btp.gatts_start_server(self.lt)

        value = "FF" * 280
        btp.gatts_set_val(self.lt, desc_id, value)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_prim_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)

        btp.gattc_disc_all_desc_rsp(self.iut, db)

        db.print_db()

        dsc = db.find_dsc_by_uuid(PTS_DB.DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        btp.gattc_read_long(self.iut,
                            self.lt.stack.gap.iut_addr_get(),
                            dsc.handle, 0)

        val = GattValue()
        btp.gattc_read_long_rsp(self.iut, val)

        self.assertEqual(val.att_rsp, "No error")
        self.assertEqual(val.value, value)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_write_characteristic(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        char_id = btp.gatts_add_char(self.lt, 0, Prop.read | Prop.write,
                                     Perm.read | Perm.write,
                                     PTS_DB.CHR_READ_WRITE)
        btp.gatts_start_server(self.lt)

        init_value = "123456"
        btp.gatts_set_val(self.lt, char_id, init_value)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        new_value = "FFFFFF"
        btp.gattc_write(self.iut,
                        self.lt.stack.gap.iut_addr_get(),
                        chr.value_handle,
                        new_value)

        future_lt = btp.gatts_attr_value_changed_ev(self.lt)

        val = GattValue()
        btp.gattc_write_rsp(self.iut, val)
        self.assertEqual(val.att_rsp, "No error")

        wait_futures([future_lt], timeout=EV_TIMEOUT)

        hdl, data = future_lt.result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_write_descriptor(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        btp.gatts_add_char(self.lt, 0, Prop.read | Prop.write,
                           Perm.read | Perm.write,
                           PTS_DB.CHR_READ_WRITE)
        desc_id = btp.gatts_add_desc(self.lt, 0, Perm.read | Perm.write,
                                     PTS_DB.DSC_READ_WRITE)
        btp.gatts_start_server(self.lt)

        init_value = "123456"
        btp.gatts_set_val(self.lt, desc_id, init_value)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_prim_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)

        btp.gattc_disc_all_desc_rsp(self.iut, db)

        db.print_db()

        dsc = db.find_dsc_by_uuid(PTS_DB.DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        new_value = "FFFFFF"
        btp.gattc_write(self.iut,
                        self.lt.stack.gap.iut_addr_get(),
                        dsc.handle,
                        new_value)

        future_lt = btp.gatts_attr_value_changed_ev(self.lt)

        val = GattValue()
        btp.gattc_write_rsp(self.iut, val)
        self.assertEqual(val.att_rsp, "No error")

        wait_futures([future_lt], timeout=EV_TIMEOUT)

        hdl, data = future_lt.result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_write_long_characteristic(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        char_id = btp.gatts_add_char(self.lt, 0, Prop.read | Prop.write,
                                     Perm.read | Perm.write,
                                     PTS_DB.CHR_READ_WRITE)
        btp.gatts_start_server(self.lt)

        init_value = "00" * 100
        btp.gatts_set_val(self.lt, char_id, init_value)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        new_value = "FF" * 100
        btp.gattc_write_long(self.iut,
                             self.lt.stack.gap.iut_addr_get(),
                             chr.value_handle,
                             0, new_value)

        future_lt = btp.gatts_attr_value_changed_ev(self.lt)

        val = GattValue()
        btp.gattc_write_long_rsp(self.iut, val)
        self.assertEqual(val.att_rsp, "No error")

        wait_futures([future_lt], timeout=EV_TIMEOUT)

        hdl, data = future_lt.result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_write_long_descriptor(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        btp.gatts_add_char(self.lt, 0, Prop.read | Prop.write,
                           Perm.read | Perm.write,
                           PTS_DB.CHR_READ_WRITE)
        desc_id = btp.gatts_add_desc(self.lt, 0, Perm.read | Perm.write,
                                     PTS_DB.DSC_READ_WRITE)
        btp.gatts_start_server(self.lt)

        init_value = "00" * 100
        btp.gatts_set_val(self.lt, desc_id, init_value)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_prim_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)

        btp.gattc_disc_all_desc_rsp(self.iut, db)

        db.print_db()

        dsc = db.find_dsc_by_uuid(PTS_DB.DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        new_value = "FF" * 100
        btp.gattc_write_long(self.iut,
                             self.lt.stack.gap.iut_addr_get(),
                             dsc.handle,
                             0, new_value)

        future_lt = btp.gatts_attr_value_changed_ev(self.lt)

        val = GattValue()
        btp.gattc_write_long_rsp(self.iut, val)
        self.assertEqual(val.att_rsp, "No error")

        wait_futures([future_lt], timeout=EV_TIMEOUT)

        hdl, data = future_lt.result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_notification(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        char_id = btp.gatts_add_char(self.lt, 0,
                                     Prop.read | Prop.write |
                                     Prop.nofity | Prop.indicate,
                                     Perm.read | Perm.write,
                                     PTS_DB.CHR_READ_WRITE)
        btp.gatts_add_desc(self.lt, 0, Perm.read | Perm.write, UUID.CCC)
        btp.gatts_start_server(self.lt)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        db = GattDB()
        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)
        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)
        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)
        btp.gattc_disc_all_desc_rsp(self.iut, db)
        db.print_db()

        dsc = db.find_dsc_by_uuid(UUID.CCC)
        self.assertIsNotNone(dsc)

        btp.gattc_cfg_notify(self.iut,
                             self.lt.stack.gap.iut_addr_get(),
                             1, dsc.handle)
        time.sleep(1)
        future_iut = btp.gattc_notification_ev(self.iut)
        btp.gatts_set_val(self.lt, char_id, "0001")
        wait_futures([future_iut], timeout=EV_TIMEOUT)

        result = future_iut.result()
        self.assertTrue(verify_notification_ev(result,
                                               self.lt.stack.gap.iut_addr_get(),
                                               0x01, chr.value_handle, "0001"))

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_indication(self):
        btp.gatts_add_svc(self.lt, 0, PTS_DB.SVC)
        char_id = btp.gatts_add_char(self.lt, 0,
                                     Prop.read | Prop.write |
                                     Prop.nofity | Prop.indicate,
                                     Perm.read | Perm.write,
                                     PTS_DB.CHR_READ_WRITE)
        btp.gatts_add_desc(self.lt, 0, Perm.read | Perm.write, UUID.CCC)
        btp.gatts_start_server(self.lt)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        db = GattDB()
        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)
        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)
        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut,
                                self.lt.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)
        btp.gattc_disc_all_desc_rsp(self.iut, db)
        db.print_db()

        dsc = db.find_dsc_by_uuid(UUID.CCC)
        self.assertIsNotNone(dsc)

        btp.gattc_cfg_indicate(self.iut,
                               self.lt.stack.gap.iut_addr_get(),
                               1, dsc.handle)
        time.sleep(1)
        btp.gatts_set_val(self.lt, char_id, "0001")

        future_iut = btp.gattc_notification_ev(self.iut)
        btp.gatts_set_val(self.lt, char_id, "0001")
        wait_futures([future_iut], timeout=EV_TIMEOUT)

        result = future_iut.result()
        self.assertTrue(verify_notification_ev(result,
                                               self.lt.stack.gap.iut_addr_get(),
                                               0x02, chr.value_handle, "0001"))

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)


class GAPTestCaseLT2(BTPTestCaseLT2):
    def __init__(self, testname, iut, lt1, lt2):
        super(__class__, self).__init__(testname, iut, lt1, lt2)

    def setUp(self):
        super(__class__, self).setUp()
        preconditions(self.iut)
        preconditions(self.lt1)
        preconditions(self.lt2)

    def tearDown(self):
        super(__class__, self).tearDown()

    def test_advertising(self):
        connection_procedure(self, central=self.lt1, peripheral=self.iut)
        connection_procedure(self, central=self.lt2, peripheral=self.iut)

        disconnection_procedure(self, central=self.lt1, peripheral=self.iut)
        disconnection_procedure(self, central=self.lt2, peripheral=self.iut)

    def test_connection(self):
        connection_procedure(self, central=self.iut, peripheral=self.lt1)
        connection_procedure(self, central=self.iut, peripheral=self.lt2)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt1)
        disconnection_procedure(self, central=self.iut, peripheral=self.lt2)
