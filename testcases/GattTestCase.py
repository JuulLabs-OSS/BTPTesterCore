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
    def __init__(self, testname, iut1, iut2):
        super(__class__, self).__init__(testname, iut1, iut2)

    def setUp(self):
        super(__class__, self).setUp()
        preconditions(self.iut1)
        preconditions(self.iut2)

    def tearDown(self):
        super(__class__, self).tearDown()

    def test_btp_GATT_CL_GAD_1(self):
        """
        Verify that a Generic Attribute Profile client discovers Primary
        Services in a GATT server.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_prim_svcs(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get())

        db = GattDB()
        btp.gattc_disc_prim_svcs_rsp(self.iut1, db)

        self.assertIsNotNone(db.find_svc_by_uuid(PTS_DB.SVC))

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAD_2(self):
        """
        Verify that a Generic Attribute Profile client can discover Primary
        Services selected by service UUID, using 16-bit and 128-bit UUIDs.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_prim_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut1, db)

        self.assertIsNotNone(db.find_svc_by_uuid(PTS_DB.SVC))

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAD_3(self):
        """
        Verify that a Generic Attribute Profile client can find include service
        declarations within a specified service definition on a server.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_prim_svcs(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get())

        db = GattDB()
        btp.gattc_disc_prim_svcs_rsp(self.iut1, db)

        for svc in db.get_services():
            start_hdl, end_hdl = svc.handle, svc.end_hdl

            btp.gattc_find_included(self.iut1,
                                    self.iut2.stack.gap.iut_addr_get(),
                                    start_hdl, end_hdl)

            btp.gattc_find_included_rsp(self.iut1, db)

        db.print_db()

        self.assertIsNotNone(db.find_inc_svc_by_uuid(PTS_DB.INC_SVC))

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAD_4(self):
        """
        Verify that a Generic Attribute Profile client can discover
        characteristic declarations within a specified service definition.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_prim_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut1, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut1, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAD_5(self):
        """
        Verify that a Generic Attribute Profile client can discover
        characteristics of a specified service, using 16-bit and 128-bit
        characteristic UUIDs.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_chrc_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut1, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)

        self.assertIsNotNone(chr)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAD_6(self):
        """
        Verify that a Generic Attribute Profile client can find all Descriptors
        of a specified Characteristic.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_prim_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut1, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut1, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)

        btp.gattc_disc_all_desc_rsp(self.iut1, db)

        db.print_db()

        dsc = db.find_dsc_by_uuid(PTS_DB.DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAR_1(self):
        """
        Verify that a Generic Attribute Profile client can read a
        Characteristic Value selected by handle.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_chrc_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut1, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        btp.gattc_read(self.iut1,
                       self.iut2.stack.gap.iut_addr_get(),
                       chr.value_handle)

        val = GattValue()
        btp.gattc_read_rsp(self.iut1, val)

        self.assertEqual(val.att_rsp, "No error")

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAR_2(self):
        """
        Verify that a Generic Attribute Profile client can read a Characteristic
        Value by selected handle. The Characteristic Value length is unknown
        to the client and might be long.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_chrc_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.LONG_CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut1, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.LONG_CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        btp.gattc_read_long(self.iut1,
                            self.iut2.stack.gap.iut_addr_get(),
                            chr.value_handle, 0)

        val = GattValue()
        btp.gattc_read_long_rsp(self.iut1, val)

        self.assertEqual(val.att_rsp, "No error")
        # self.assertEqual(val.value, value)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAR_3(self):
        """
        Verify that a Generic Attribute Profile client can read a characteristic
        descriptor selected by handle.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_prim_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut1, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut1, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)

        btp.gattc_disc_all_desc_rsp(self.iut1, db)

        db.print_db()

        dsc = db.find_dsc_by_uuid(PTS_DB.DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        btp.gattc_read(self.iut1,
                       self.iut2.stack.gap.iut_addr_get(),
                       dsc.handle)

        val = GattValue()
        btp.gattc_read_rsp(self.iut1, val)

        self.assertEqual(val.att_rsp, "No error")

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAR_4(self):
        """
        Verify that a Generic Attribute Profile client can read a characteristic
        descriptor by selected handle. The Characteristic Descriptor length
        is unknown to the client and might be long.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_prim_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut1, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut1, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)

        btp.gattc_disc_all_desc_rsp(self.iut1, db)

        db.print_db()

        dsc = db.find_dsc_by_uuid(PTS_DB.LONG_DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        btp.gattc_read_long(self.iut1,
                            self.iut2.stack.gap.iut_addr_get(),
                            dsc.handle, 0)

        val = GattValue()
        btp.gattc_read_long_rsp(self.iut1, val)

        self.assertEqual(val.att_rsp, "No error")

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAW_1(self):
        """
        Verify that a Generic Attribute Profile client can write
        a Characteristic Value selected by handle.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_chrc_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut1, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        new_value = "FF"
        btp.gattc_write(self.iut1,
                        self.iut2.stack.gap.iut_addr_get(),
                        chr.value_handle,
                        new_value)

        future_iut2 = btp.gatts_attr_value_changed_ev(self.iut2)

        val = GattValue()
        btp.gattc_write_rsp(self.iut1, val)
        self.assertEqual(val.att_rsp, "No error")

        wait_futures([future_iut2], timeout=EV_TIMEOUT)

        hdl, data = future_iut2.result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAW_2(self):
        """
        Verify that a Generic Attribute Profile client can write a long
        Characteristic Value selected by handle.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_chrc_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.LONG_CHR_READ_WRITE)

        db = GattDB()
        btp.gattc_disc_chrc_uuid_rsp(self.iut1, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.LONG_CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        new_value = "FF" * 100
        btp.gattc_write_long(self.iut1,
                             self.iut2.stack.gap.iut_addr_get(),
                             chr.value_handle,
                             0, new_value)

        future_iut2 = btp.gatts_attr_value_changed_ev(self.iut2)

        val = GattValue()
        btp.gattc_write_long_rsp(self.iut1, val)
        self.assertEqual(val.att_rsp, "No error")

        wait_futures([future_iut2], timeout=EV_TIMEOUT)

        hdl, data = future_iut2.result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAW_3(self):
        """
        Verify that a Generic Attribute Profile client can write
        a characteristic descriptor selected by handle.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_prim_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut1, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut1, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)

        btp.gattc_disc_all_desc_rsp(self.iut1, db)

        db.print_db()

        dsc = db.find_dsc_by_uuid(PTS_DB.DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        new_value = "FF"
        btp.gattc_write(self.iut1,
                        self.iut2.stack.gap.iut_addr_get(),
                        dsc.handle,
                        new_value)

        future_iut2 = btp.gatts_attr_value_changed_ev(self.iut2)

        val = GattValue()
        btp.gattc_write_rsp(self.iut1, val)
        self.assertEqual(val.att_rsp, "No error")

        wait_futures([future_iut2], timeout=EV_TIMEOUT)

        hdl, data = future_iut2.result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAW_4(self):
        """
        Verify that a Generic Attribute Profile client can write a long
        characteristic descriptor selected by handle.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gattc_disc_prim_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 PTS_DB.SVC)

        db = GattDB()
        btp.gattc_disc_prim_uuid_rsp(self.iut1, db)

        svc = db.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        btp.gattc_disc_all_chrc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                start_hdl, end_hdl)

        btp.gattc_disc_all_chrc_rsp(self.iut1, db)

        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)

        btp.gattc_disc_all_desc_rsp(self.iut1, db)

        db.print_db()

        dsc = db.find_dsc_by_uuid(PTS_DB.LONG_DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        new_value = "FF" * 100
        btp.gattc_write_long(self.iut1,
                             self.iut2.stack.gap.iut_addr_get(),
                             dsc.handle,
                             0, new_value)

        future_iut2 = btp.gatts_attr_value_changed_ev(self.iut2)

        val = GattValue()
        btp.gattc_write_long_rsp(self.iut1, val)
        self.assertEqual(val.att_rsp, "No error")

        wait_futures([future_iut2], timeout=EV_TIMEOUT)

        hdl, data = future_iut2.result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAN_1(self):
        """
        Verify that a Generic Attribute Profile client can receive
        a Characteristic Value Notification and report that to the Upper Tester.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        db = GattDB()
        btp.gattc_disc_chrc_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_NOTIFY)
        btp.gattc_disc_chrc_uuid_rsp(self.iut1, db)
        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_NOTIFY)
        self.assertIsNotNone(chr)
        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)
        btp.gattc_disc_all_desc_rsp(self.iut1, db)
        db.print_db()

        dsc = db.find_dsc_by_uuid(UUID.CCC)
        self.assertIsNotNone(dsc)

        future_iut1 = btp.gattc_notification_ev(self.iut1)

        btp.gattc_cfg_notify(self.iut1,
                             self.iut2.stack.gap.iut_addr_get(),
                             1, dsc.handle)

        wait_futures([future_iut1], timeout=EV_TIMEOUT)
        result = future_iut1.result()

        self.assertTrue(verify_notification_ev(result,
                                               self.iut2.stack.gap.iut_addr_get(),
                                               0x01, chr.value_handle))

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAI_1(self):
        """
        Verify that a Generic Attribute Profile client can receive
        a Characteristic Value Notification and report that to the Upper Tester.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        db = GattDB()
        btp.gattc_disc_chrc_uuid(self.iut1,
                                 self.iut2.stack.gap.iut_addr_get(),
                                 0x0001, 0xffff, PTS_DB.CHR_NOTIFY)
        btp.gattc_disc_chrc_uuid_rsp(self.iut1, db)
        db.print_db()

        chr = db.find_chr_by_uuid(PTS_DB.CHR_NOTIFY)
        self.assertIsNotNone(chr)
        end_hdl = db.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        btp.gattc_disc_all_desc(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(),
                                chr.value_handle + 1, end_hdl)
        btp.gattc_disc_all_desc_rsp(self.iut1, db)
        db.print_db()

        dsc = db.find_dsc_by_uuid(UUID.CCC)
        self.assertIsNotNone(dsc)

        future_iut1 = btp.gattc_notification_ev(self.iut1)

        btp.gattc_cfg_indicate(self.iut1,
                               self.iut2.stack.gap.iut_addr_get(),
                               1, dsc.handle)

        wait_futures([future_iut1], timeout=EV_TIMEOUT)
        result = future_iut1.result()

        self.assertTrue(verify_notification_ev(result,
                                               self.iut2.stack.gap.iut_addr_get(),
                                               0x02, chr.value_handle))

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)


