#
# Copyright (c) 2019 JUUL Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import time

from pybtp import btp
from pybtp.types import PTS_DB, Prop, Perm, UUID
from pybtp.utils import wait_futures
from stack.gatt import GattDB, GattValue
from testcases.BTPTestCase import BTPTestCase
from testcases.utils import preconditions, connection_procedure, \
    disconnection_procedure, EV_TIMEOUT, verify_notification_ev


class GattTestCase(BTPTestCase):
    def __init__(self, testname, iut, lt):
        super(__class__, self).__init__(testname, iut, lt)

    def setUp(self):
        super(__class__, self).setUp()
        preconditions(self.iut)
        preconditions(self.lt)

    def tearDown(self):
        super(__class__, self).tearDown()

    def test_gattc_discover_primary_svcs(self):
        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_prim_svcs(self.iut,
                                 self.lt.stack.gap.iut_addr_get())

        db = GattDB()
        btp.gattc_disc_prim_svcs_rsp(self.iut, db)

        self.assertIsNotNone(db.find_svc_by_uuid(PTS_DB.SVC))

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_discover_primary_uuid(self):
        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_prim_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut, db)

        self.assertIsNotNone(db.find_svc_by_uuid(PTS_DB.SVC))

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_find_incl_svcs(self):
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

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_read_descriptor(self):
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

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_read_long_characteristic(self):
        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.LONG_CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.LONG_CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        btp.gattc_read_long(self.iut,
                            self.lt.stack.gap.iut_addr_get(),
                            chr.value_handle, 0)

        val = GattValue()
        btp.gattc_read_long_rsp(self.iut, val)

        self.assertEqual(val.att_rsp, "No error")
        # self.assertEqual(val.value, value)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_read_long_descriptor(self):
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

        dsc = db.find_dsc_by_uuid(PTS_DB.LONG_DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        btp.gattc_read_long(self.iut,
                            self.lt.stack.gap.iut_addr_get(),
                            dsc.handle, 0)

        val = GattValue()
        btp.gattc_read_long_rsp(self.iut, val)

        self.assertEqual(val.att_rsp, "No error")

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_write_characteristic(self):
        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        new_value = "FF"
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

        new_value = "FF"
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
        connection_procedure(self, central=self.iut, peripheral=self.lt)

        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.LONG_CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.LONG_CHR_READ_WRITE)
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

        dsc = db.find_dsc_by_uuid(PTS_DB.LONG_DSC_READ_WRITE)
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
        connection_procedure(self, central=self.iut, peripheral=self.lt)

        db = GattDB()
        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_NOTIFY)
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)
        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_NOTIFY)
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

        future_iut = btp.gattc_notification_ev(self.iut)

        btp.gattc_cfg_notify(self.iut,
                             self.lt.stack.gap.iut_addr_get(),
                             1, dsc.handle)

        wait_futures([future_iut], timeout=EV_TIMEOUT)
        result = future_iut.result()

        self.assertTrue(verify_notification_ev(result,
                                               self.lt.stack.gap.iut_addr_get(),
                                               0x01, chr.value_handle))

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)

    def test_gattc_indication(self):
        connection_procedure(self, central=self.iut, peripheral=self.lt)

        db = GattDB()
        btp.gattc_disc_chrc_uuid(self.iut,
                                 self.lt.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_NOTIFY)
        btp.gattc_disc_chrc_uuid_rsp(self.iut, db)
        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_NOTIFY)
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

        future_iut = btp.gattc_notification_ev(self.iut)

        btp.gattc_cfg_indicate(self.iut,
                               self.lt.stack.gap.iut_addr_get(),
                               1, dsc.handle)

        wait_futures([future_iut], timeout=EV_TIMEOUT)
        result = future_iut.result()

        self.assertTrue(verify_notification_ev(result,
                                               self.lt.stack.gap.iut_addr_get(),
                                               0x02, chr.value_handle))

        disconnection_procedure(self, central=self.iut, peripheral=self.lt)


