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
import sys
from binascii import hexlify

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

    def disc_prim_svcs(self, iut1, iut2):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_disc_prim_svcs(iut1, iut2.stack.gap.iut_addr_get())
            stack.gatt_cl.wait_for_prim_svcs()
            db = stack.gatt_cl.db
        else:
            btp.gattc_disc_prim_svcs(iut1, iut2.stack.gap.iut_addr_get())
            db = GattDB()
            btp.gattc_disc_prim_svcs_rsp(self.iut1, db)

        db.print_db()
        return db


    def disc_prim_uuid(self, iut1, iut2, uuid):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_disc_prim_uuid(iut1, iut2.stack.gap.iut_addr_get(), uuid)
            stack.gatt_cl.wait_for_prim_svcs()
            db = stack.gatt_cl.db
        else:
            btp.gattc_disc_prim_uuid(iut1, iut2.stack.gap.iut_addr_get(), uuid)
            db = GattDB()
            btp.gattc_disc_prim_uuid_rsp(self.iut1, db)

        db.print_db()
        return db


    def find_included_svcs(self, iut1, iut2, db):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_find_included(iut1, iut2.stack.gap.iut_addr_get(), '0001', 'FFFF')
            stack.gatt_cl.wait_for_incl_svcs()
            db = stack.gatt_cl.db
        else:
            for svc in db.get_services():
                start_hdl, end_hdl = svc.handle, svc.end_hdl

                btp.gattc_find_included(self.iut1,
                                        self.iut2.stack.gap.iut_addr_get(),
                                        start_hdl, end_hdl)

                btp.gattc_find_included_rsp(self.iut1, db)
            db.print_db()

        return db


    def disc_all_chrc(self, iut1, iut2, start_hdl, end_hdl):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_disc_all_chrc(iut1, iut2.stack.gap.iut_addr_get(),
                                      start_hdl, end_hdl)
            stack.gatt_cl.wait_for_chrcs()
            db = stack.gatt_cl.db
        else:
            db = GattDB()
            btp.gattc_disc_all_chrc(iut1, iut2.stack.gap.iut_addr_get(),
                                      start_hdl, end_hdl)
            btp.gattc_disc_all_chrc_rsp(self.iut1, db)
            db.print_db()

        return db

    def disc_chrc_uuid(self, iut1, iut2, start_hdl, stop_hdl, uuid):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_disc_chrc_uuid(iut1, iut2.stack.gap.iut_addr_get(),
                                      start_hdl, stop_hdl, uuid)
            stack.gatt_cl.wait_for_chrcs()
            db = stack.gatt_cl.db
        else:
            db = GattDB()
            btp.gattc_disc_chrc_uuid(iut1, iut2.stack.gap.iut_addr_get(),
                                      start_hdl, stop_hdl, uuid)
            btp.gattc_disc_chrc_uuid_rsp(self.iut1, db)

            db.print_db()

        return db


    def disc_all_desc(self, iut1, iut2, start_hdl, stop_hdl):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_disc_all_desc(iut1, iut2.stack.gap.iut_addr_get(),
                                      start_hdl, stop_hdl)
            stack.gatt_cl.wait_for_descs()
            db = stack.gatt_cl.db
        else:
            db = GattDB()
            btp.gattc_disc_all_desc(iut1, iut2.stack.gap.iut_addr_get(),
                                    start_hdl, stop_hdl)
            btp.gattc_disc_all_desc_rsp(self.iut1, db)

            db.print_db()
        return db


    def read(self, iut1, iut2, hdl):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_read(iut1, iut2.stack.gap.iut_addr_get(), hdl)
            stack.gatt_cl.wait_for_read()
            return stack.gatt_cl.verify_values[0]
        else:
            val = GattValue()
            btp.gattc_read(iut1, iut2.stack.gap.iut_addr_get(), hdl)
            btp.gattc_read_rsp(self.iut1, val)
            return val.att_rsp


    def read_long(self, iut1, iut2, hdl, off, modif_off=None):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_read_long(iut1, iut2.stack.gap.iut_addr_get(), hdl, off, modif_off)
            stack.gatt_cl.wait_for_read()
            return stack.gatt_cl.verify_values[0]
        else:
            val = GattValue()
            btp.gattc_read_long(iut1, iut2.stack.gap.iut_addr_get(), hdl, off, modif_off)
            btp.gattc_read_long_rsp(self.iut1, val)
            return val.att_rsp


    def write(self, iut1, iut2, hdl, val):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_write(iut1, iut2.stack.gap.iut_addr_get(), hdl, val)
            future_iut2 = btp.gatts_attr_value_changed_ev(self.iut2)
            stack.gatt_cl.wait_for_write_rsp()
            return (stack.gatt_cl.verify_values[0], future_iut2)
        else:
            value = GattValue()
            btp.gattc_write(iut1, iut2.stack.gap.iut_addr_get(), hdl, val)
            future_iut2 = btp.gatts_attr_value_changed_ev(self.iut2)
            btp.gattc_write_rsp(self.iut1, value)
            return (value.att_rsp, future_iut2)


    def write_long(self, iut1, iut2, hdl, off, val):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_write_long(iut1, iut2.stack.gap.iut_addr_get(), hdl, off, val)
            future_iut2 = btp.gatts_attr_value_changed_ev(self.iut2)
            stack.gatt_cl.wait_for_write_rsp()
            return (stack.gatt_cl.verify_values[0], future_iut2)
        else:
            value = GattValue()
            btp.gattc_write_long(iut1, iut2.stack.gap.iut_addr_get(), hdl, off, val)
            future_iut2 = btp.gatts_attr_value_changed_ev(self.iut2)
            btp.gattc_write_long_rsp(self.iut1, value)
            return (value.att_rsp, future_iut2)


    def cfg_notify(self, iut1, iut2, enable, hdl):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_cfg_notify(iut1, iut2.stack.gap.iut_addr_get(), enable, hdl)
            stack.gatt_cl.wait_for_write_rsp()
            self.assertEqual(stack.gatt_cl.verify_values[0], "No error")
            stack.gatt_cl.wait_for_notifications(expected_count=1)
            return stack.gatt_cl.notifications[0]
        else:
            value = GattValue()
            future_iut1 = btp.gattc_notification_ev(self.iut1)
            btp.gattc_cfg_notify(iut1, iut2.stack.gap.iut_addr_get(), enable, hdl)
            btp.gattc_write_rsp(self.iut1, value)
            self.assertEqual(value.att_rsp, "No error")
            wait_futures([future_iut1], timeout=EV_TIMEOUT)
            result = future_iut1.result()
            return result


    def cfg_indicate(self, iut1, iut2, enable, hdl):
        stack = self.iut1.stack
        if stack.gatt_cl:
            btp.gatt_cl_cfg_indicate(iut1, iut2.stack.gap.iut_addr_get(), enable, hdl)
            stack.gatt_cl.wait_for_write_rsp()
            self.assertEqual(stack.gatt_cl.verify_values[0], "No error")
            stack.gatt_cl.wait_for_notifications(expected_count=1)
            return stack.gatt_cl.notifications[0]
        else:
            value = GattValue()
            future_iut1 = btp.gattc_notification_ev(self.iut1)
            btp.gattc_cfg_indicate(iut1, iut2.stack.gap.iut_addr_get(), enable, hdl)
            btp.gattc_write_rsp(self.iut1, value)
            self.assertEqual(value.att_rsp, "No error")
            wait_futures([future_iut1], timeout=EV_TIMEOUT)
            result = future_iut1.result()
            return result


    def test_btp_GATT_CL_GAD_1(self):
        """
        Verify that a Generic Attribute Profile client discovers Primary
        Services in a GATT server.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        db = self.disc_prim_svcs(self.iut1, self.iut2)

        self.assertIsNotNone(db.find_svc_by_uuid(PTS_DB.SVC))
        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAD_2(self):
        """
        Verify that a Generic Attribute Profile client can discover Primary
        Services selected by service UUID, using 16-bit and 128-bit UUIDs.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        db = self.disc_prim_uuid(self.iut1, self.iut2, PTS_DB.SVC)

        self.assertIsNotNone(db.find_svc_by_uuid(PTS_DB.SVC))
        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAD_3(self):
        """
        Verify that a Generic Attribute Profile client can find include service
        declarations within a specified service definition on a server.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        db = self.disc_prim_svcs(self.iut1, self.iut2)
        db_2 = self.find_included_svcs(self.iut1, self.iut2, db)

        self.assertIsNotNone(db_2.find_inc_svc_by_uuid(PTS_DB.INC_SVC))
        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAD_4(self):
        """
        Verify that a Generic Attribute Profile client can discover
        characteristic declarations within a specified service definition.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        svcs = self.disc_prim_uuid(self.iut1, self.iut2, PTS_DB.SVC)
        svc = svcs.find_svc_by_uuid(PTS_DB.SVC)

        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl
        chars = self.disc_all_chrc(self.iut1, self.iut2, start_hdl, end_hdl)

        chr = chars.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)

        self.assertIsNotNone(chr)
        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAD_5(self):
        """
        Verify that a Generic Attribute Profile client can discover
        characteristics of a specified service, using 16-bit and 128-bit
        characteristic UUIDs.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        db = self.disc_chrc_uuid(self.iut1, self.iut2,
                                 0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)
        chr = db.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)

        self.assertIsNotNone(chr)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAD_6(self):
        """
        Verify that a Generic Attribute Profile client can find all Descriptors
        of a specified Characteristic.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)
        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        db = self.disc_prim_uuid(self.iut1, self.iut2, PTS_DB.SVC)
        svc = db.find_svc_by_uuid(PTS_DB.SVC)

        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl
        chars = self.disc_all_chrc(self.iut1, self.iut2, start_hdl, end_hdl)
        chr = chars.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)

        self.assertIsNotNone(chr)

        end_hdl = chars.find_characteristic_end(chr.handle)

        self.assertIsNotNone(end_hdl)

        desc = self.disc_all_desc(self.iut1, self.iut2, chr.value_handle + 1, end_hdl)
        dsc = desc.find_dsc_by_uuid(PTS_DB.DSC_READ_WRITE)

        self.assertIsNotNone(dsc)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAR_1(self):
        """
        Verify that a Generic Attribute Profile client can read a
        Characteristic Value selected by handle.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        chars = self.disc_chrc_uuid(self.iut1, self.iut2,
                                    0x0001, 0xffff,PTS_DB.CHR_READ_WRITE)
        chr = chars.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)

        self.assertIsNotNone(chr)

        rsp = self.read(self.iut1, self.iut2, chr.value_handle)

        self.assertEqual(rsp, "No error")

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAR_2(self):
        """
        Verify that a Generic Attribute Profile client can read a Characteristic
        Value by selected handle. The Characteristic Value length is unknown
        to the client and might be long.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        chars = self.disc_chrc_uuid(self.iut1, self.iut2,
                                    0x0001, 0xffff, PTS_DB.LONG_CHR_READ_WRITE)
        chr = chars.find_chr_by_uuid(PTS_DB.LONG_CHR_READ_WRITE)

        self.assertIsNotNone(chr)

        rsp = self.read_long(self.iut1, self.iut2, chr.value_handle, 0, 40)

        self.assertEqual(rsp, "No error")

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAR_3(self):
        """
        Verify that a Generic Attribute Profile client can read a characteristic
        descriptor selected by handle.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        svcs = self.disc_prim_uuid(self.iut1, self.iut2, PTS_DB.SVC)
        svc = svcs.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        chars = self.disc_all_chrc(self.iut1, self.iut2, start_hdl, end_hdl)
        chr = chars.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = chars.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        desc = self.disc_all_desc(self.iut1, self.iut2, chr.value_handle + 1, end_hdl)
        dsc = desc.find_dsc_by_uuid(PTS_DB.DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        rsp = self.read(self.iut1, self.iut2, dsc.handle)

        self.assertEqual(rsp, "No error")

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAR_4(self):
        """
        Verify that a Generic Attribute Profile client can read a characteristic
        descriptor by selected handle. The Characteristic Descriptor length
        is unknown to the client and might be long.
        """
        stack = self.iut1.stack

        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        svcs = self.disc_prim_uuid(self.iut1, self.iut2, PTS_DB.SVC)
        svc = svcs.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl

        chars = self.disc_all_chrc(self.iut1, self.iut2, start_hdl, end_hdl)
        chr = chars.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = chars.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        desc = self.disc_all_desc(self.iut1, self.iut2, chr.value_handle + 1, end_hdl)
        dsc = desc.find_dsc_by_uuid(PTS_DB.LONG_DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        rsp = self.read_long(self.iut1, self.iut2, dsc.handle, 0, 40)

        self.assertEqual(rsp, "No error")

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAW_1(self):
        """
        Verify that a Generic Attribute Profile client can write
        a Characteristic Value selected by handle.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        chars = self.disc_chrc_uuid(self.iut1,
                                    self.iut2,
                                    0x0001, 0xffff, PTS_DB.CHR_READ_WRITE)
        chr = chars.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)
        new_value = "FF"
        rsp = self.write(self.iut1, self.iut2, chr.value_handle, new_value)
        self.assertEqual(rsp[0], "No error")

        wait_futures([rsp[1]], timeout=EV_TIMEOUT)

        hdl, data = rsp[1].result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAW_2(self):
        """
        Verify that a Generic Attribute Profile client can write a long
        Characteristic Value selected by handle.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        chars = self.disc_chrc_uuid(self.iut1,
                                    self.iut2,
                                    0x0001, 0xffff, PTS_DB.LONG_CHR_READ_WRITE)
        chr = chars.find_chr_by_uuid(PTS_DB.LONG_CHR_READ_WRITE)
        self.assertIsNotNone(chr)
        new_value = "FF" * 100
        rsp = self.write_long(self.iut1, self.iut2, chr.value_handle, 0, new_value)
        self.assertEqual(rsp[0], "No error")

        wait_futures([rsp[1]], timeout=EV_TIMEOUT)

        hdl, data = rsp[1].result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAW_3(self):
        """
        Verify that a Generic Attribute Profile client can write
        a characteristic descriptor selected by handle.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        svcs = self.disc_prim_uuid(self.iut1, self.iut2, PTS_DB.SVC)
        svc = svcs.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl
        chars = self.disc_all_chrc(self.iut1, self.iut2, start_hdl, end_hdl)
        chr = chars.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = chars.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        desc = self.disc_all_desc(self.iut1, self.iut2, chr.value_handle + 1, end_hdl)
        dsc = desc.find_dsc_by_uuid(PTS_DB.DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        new_value = "FF"
        rsp = self.write(self.iut1, self.iut2, dsc.handle, new_value)

        wait_futures([rsp[1]], timeout=EV_TIMEOUT)

        hdl, data = rsp[1].result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAW_4(self):
        """
        Verify that a Generic Attribute Profile client can write a long
        characteristic descriptor selected by handle.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        svcs = self.disc_prim_uuid(self.iut1, self.iut2, PTS_DB.SVC)
        svc = svcs.find_svc_by_uuid(PTS_DB.SVC)
        self.assertIsNotNone(svc)

        start_hdl, end_hdl = svc.handle, svc.end_hdl
        chars = self.disc_all_chrc(self.iut1, self.iut2, start_hdl, end_hdl)
        chr = chars.find_chr_by_uuid(PTS_DB.CHR_READ_WRITE)
        self.assertIsNotNone(chr)

        end_hdl = chars.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        desc = self.disc_all_desc(self.iut1, self.iut2, chr.value_handle + 1, end_hdl)
        dsc = desc.find_dsc_by_uuid(PTS_DB.LONG_DSC_READ_WRITE)
        self.assertIsNotNone(dsc)

        new_value = "FF" * 100
        rsp = self.write_long(self.iut1, self.iut2, dsc.handle, 0, new_value)
        self.assertEqual(rsp[0], "No error")

        wait_futures([rsp[1]], timeout=EV_TIMEOUT)

        hdl, data = rsp[1].result()
        self.assertEqual(data, new_value)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAN_1(self):
        """
        Verify that a Generic Attribute Profile client can receive
        a Characteristic Value Notification and report that to the Upper Tester.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        chars = self.disc_chrc_uuid(self.iut1, self.iut2,
                                    0x0001, 0xffff, PTS_DB.CHR_NOTIFY)
        chr = chars.find_chr_by_uuid(PTS_DB.CHR_NOTIFY)
        self.assertIsNotNone(chr)
        end_hdl = chars.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        desc = self.disc_all_desc(self.iut1, self.iut2,
                                  chr.value_handle + 1, end_hdl)
        dsc = desc.find_dsc_by_uuid(UUID.CCC)
        self.assertIsNotNone(dsc)

        subscribe = self.cfg_notify(self.iut1, self.iut2, 1, dsc.handle)

        self.assertTrue(verify_notification_ev(subscribe,
                                               self.iut2.stack.gap.iut_addr_get(),
                                               0x01, chr.value_handle))

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GATT_CL_GAI_1(self):
        """
        Verify that a Generic Attribute Profile client can receive
        a Characteristic Value Notification and report that to the Upper Tester.
        """
        self.verify_skipped(sys._getframe().f_code.co_name)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        chars = self.disc_chrc_uuid(self.iut1, self.iut2,
                                    0x0001, 0xffff, PTS_DB.CHR_NOTIFY)
        chr = chars.find_chr_by_uuid(PTS_DB.CHR_NOTIFY)
        self.assertIsNotNone(chr)
        end_hdl = chars.find_characteristic_end(chr.handle)
        self.assertIsNotNone(end_hdl)

        desc = self.disc_all_desc(self.iut1, self.iut2,
                                  chr.value_handle + 1, end_hdl)
        dsc = desc.find_dsc_by_uuid(UUID.CCC)
        self.assertIsNotNone(dsc)

        subscribe = self.cfg_indicate(self.iut1, self.iut2, 1, dsc.handle)

        self.assertTrue(verify_notification_ev(subscribe,
                                               self.iut2.stack.gap.iut_addr_get(),
                                               0x02, chr.value_handle))

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)


