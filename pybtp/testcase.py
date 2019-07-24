import binascii
import os
import time
import unittest
from concurrent.futures import wait

from pybtp import btp
from pybtp.types import IOCap, AdType, UUID, PTS_DB, Prop, Perm
from stack.gatt import GattDB


def preconditions(iutctl):
    btp.core_reg_svc_gap(iutctl)
    btp.core_reg_svc_gatt(iutctl)
    iutctl.stack.gap_init()
    iutctl.stack.gatt_init()
    btp.gap_read_ctrl_info(iutctl)


def connection_procedure(testcase, central, peripheral):
    btp.gap_set_conn(peripheral)
    btp.gap_set_gendiscov(peripheral)

    uuid = os.urandom(2)
    btp.gap_adv_ind_on(peripheral, ad=[(AdType.uuid16_some, uuid)])

    btp.gap_start_discov(central)
    time.sleep(5)
    btp.gap_stop_discov(central)
    found = btp.check_discov_results_by_uuid(central,
                                             btp.btp2uuid(len(uuid), uuid))

    testcase.assertIsNotNone(found)
    peripheral.stack.gap.iut_addr_set(found.addr)

    btp.gap_conn(central, peripheral.stack.gap.iut_addr_get())

    btp.gap_wait_for_connection(central)
    btp.gap_wait_for_connection(peripheral)

    testcase.assertTrue(central.stack.gap.is_connected())
    testcase.assertTrue(peripheral.stack.gap.is_connected())


def disconnection_procedure(testcase, central, peripheral):
    btp.gap_disconn(central, peripheral.stack.gap.iut_addr_get())

    btp.gap_wait_for_disconnection(peripheral)
    btp.gap_wait_for_disconnection(central)

    testcase.assertFalse(peripheral.stack.gap.is_connected())
    testcase.assertFalse(central.stack.gap.is_connected())


def verify_conn_params(iutctl, conn_itvl_min, conn_itvl_max,
                       conn_latency, supervision_timeout):
    params = iutctl.stack.gap.get_conn_params()

    return (params.conn_itvl >= conn_itvl_min) and \
           (params.conn_itvl <= conn_itvl_max) and \
           (params.conn_latency == conn_latency) and \
           (params.supervision_timeout == supervision_timeout)


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

    def test_connection_parameter_update_master(self):
        connection_procedure(self, central=self.iut, peripheral=self.lt)

        conn_params = self.iut.stack.gap.get_conn_params()

        conn_itvl_min, conn_itvl_max, latency, supervision_timeout = (
            conn_params.conn_itvl,
            conn_params.conn_itvl,
            conn_params.conn_latency + 2,
            conn_params.supervision_timeout)

        btp.gap_conn_param_update(self.iut,
                                  self.lt.stack.gap.iut_addr_get(),
                                  conn_itvl_min, conn_itvl_max, latency,
                                  supervision_timeout)

        wait([btp.gap_conn_param_update_ev(self.iut),
              btp.gap_conn_param_update_ev(self.lt)], timeout=20)

        self.assertTrue(verify_conn_params(self.iut, conn_itvl_min,
                                           conn_itvl_max, latency,
                                           supervision_timeout))

        self.assertTrue(verify_conn_params(self.lt, conn_itvl_min,
                                           conn_itvl_max, latency,
                                           supervision_timeout))

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_pairing_jw(self):
        btp.gap_set_io_cap(self.lt, IOCap.no_input_output)
        connection_procedure(self, central=self.iut, peripheral=self.lt)
        btp.gap_pair(self.iut, self.lt.stack.gap.iut_addr_get())
        time.sleep(20)
        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_pairing_numcmp(self):
        btp.gap_set_io_cap(self.iut, IOCap.display_yesno)
        btp.gap_set_io_cap(self.lt, IOCap.display_yesno)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gap_pair(self.iut, self.lt.stack.gap.iut_addr_get())

        pk_iut = self.iut.stack.gap.get_passkey(timeout=20)
        self.assertIsNotNone(pk_iut)
        pk_lt = self.lt.stack.gap.get_passkey()
        self.assertIsNotNone(pk_lt)
        self.assertEqual(pk_iut, pk_lt)

        btp.gap_passkey_confirm(self.iut,
                                self.lt.stack.gap.iut_addr_get(), 1)

        btp.gap_passkey_confirm(self.lt,
                                self.iut.stack.gap.iut_addr_get(), 1)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_pairing_input(self):
        btp.gap_set_io_cap(self.iut, IOCap.keyboard_only)
        btp.gap_set_io_cap(self.lt, IOCap.display_only)

        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gap_pair(self.iut,
                     self.lt.stack.gap.iut_addr_get())

        pk_lt = self.lt.stack.gap.get_passkey(timeout=20)
        self.assertIsNotNone(pk_lt)

        btp.gap_passkey_entry_req_ev(self.iut,
                                     self.lt.stack.gap.iut_addr_get())

        btp.gap_passkey_entry_rsp(self.iut,
                                  self.lt.stack.gap.iut_addr_get(),
                                  pk_lt)

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

        btp.gattc_read_rsp(self.iut, store_rsp=True, store_val=True)

        verify_values = self.iut.stack.gatt.verify_values
        self.assertEqual(verify_values[0], "No error")
        self.assertEqual(verify_values[1], value)

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

        btp.gattc_read_rsp(self.iut, store_rsp=True, store_val=True)

        verify_values = self.iut.stack.gatt.verify_values
        self.assertEqual(verify_values[0], "No error")
        self.assertEqual(verify_values[1], value)

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

        btp.gattc_read_long_rsp(self.iut, store_rsp=True, store_val=True)

        verify_values = self.iut.stack.gatt.verify_values
        self.assertEqual(verify_values[0], "No error")
        self.assertEqual(verify_values[1], value)

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

        btp.gattc_read_long_rsp(self.iut, store_rsp=True, store_val=True)

        verify_values = self.iut.stack.gatt.verify_values
        self.assertEqual(verify_values[0], "No error")
        self.assertEqual(verify_values[1], value)

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

        btp.gattc_write_rsp(self.iut, store_rsp=True)

        verify_values = self.iut.stack.gatt.verify_values
        self.assertEqual(verify_values[0], "No error")

        hdl, data = btp.gatts_attr_value_changed_ev(self.lt)
        recv_val = binascii.hexlify(data[0]).decode().upper()

        self.assertEqual(recv_val, new_value)

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

        btp.gattc_write_rsp(self.iut, store_rsp=True)

        verify_values = self.iut.stack.gatt.verify_values
        self.assertEqual(verify_values[0], "No error")

        hdl, data = btp.gatts_attr_value_changed_ev(self.lt)
        recv_val = binascii.hexlify(data[0]).decode().upper()

        self.assertEqual(recv_val, new_value)

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

        btp.gattc_write_long_rsp(self.iut, store_rsp=True)

        verify_values = self.iut.stack.gatt.verify_values
        self.assertEqual(verify_values[0], "No error")

        hdl, data = btp.gatts_attr_value_changed_ev(self.lt)
        recv_val = binascii.hexlify(data[0]).decode().upper()

        self.assertEqual(recv_val, new_value)

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

        btp.gattc_write_long_rsp(self.iut, store_rsp=True)

        verify_values = self.iut.stack.gatt.verify_values
        self.assertEqual(verify_values[0], "No error")

        hdl, data = btp.gatts_attr_value_changed_ev(self.lt)
        recv_val = binascii.hexlify(data[0]).decode().upper()

        self.assertEqual(recv_val, new_value)

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

        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)

        db = GattDB()
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

        btp.gatts_set_val(self.lt,
                          char_id,
                          "0001")

        btp.gattc_notification_ev(self.iut,
                                  self.lt.stack.gap.iut_addr_get(),
                                  0x01,
                                  chr.value_handle,
                                  "0001")

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

        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)

        db = GattDB()
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

        btp.gatts_set_val(self.lt,
                          char_id,
                          "0001")

        btp.gattc_notification_ev(self.iut,
                                  self.lt.stack.gap.iut_addr_get(),
                                  0x02,
                                  chr.value_handle,
                                  "0001")

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
