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

import os

from pybtp import btp
from pybtp.types import AdType, IOCap
from pybtp.utils import wait_futures
from testcases.BTPTestCase import BTPTestCase
from testcases.utils import preconditions, find_adv_by_uuid, EV_TIMEOUT, \
    connection_procedure, disconnection_procedure, verify_address, \
    verify_conn_params


class GapTestCase(BTPTestCase):
    def __init__(self, testname, iut1, iut2):
        super(__class__, self).__init__(testname, iut1, iut2)

    def setUp(self):
        super(__class__, self).setUp()
        preconditions(self.iut1)
        preconditions(self.iut2)

    def tearDown(self):
        super(__class__, self).tearDown()

    def test_btp_GAP_DISC_GENM_1(self):
        """
        Verify the IUT1 in General Discoverable Mode and the Undirected
        Connectable Mode can be discovered by a device performing the General
        Discovery Procedure.

        The IUT1 is operating in the Peripheral role.
        """

        btp.gap_set_conn(self.iut2)
        btp.gap_set_gendiscov(self.iut2)

        uuid = os.urandom(2)
        btp.gap_adv_ind_on(self.iut2, ad=[(AdType.uuid16_some, uuid)])

        def verify_f(args):
            return find_adv_by_uuid(args, btp.btp2uuid(len(uuid), uuid))

        btp.gap_start_discov(self.iut1)
        future = btp.gap_device_found_ev(self.iut1, verify_f)
        wait_futures([future], timeout=EV_TIMEOUT)
        btp.gap_stop_discov(self.iut1)

        found = future.result()
        self.assertIsNotNone(found)

    def test_btp_GAP_CONN_GCEP_1(self):
        """
        Verify the IUT1 can perform the General Connection Establishment
        Procedure to connect to another device in the Undirected Connectable
        Mode.

        The IUT1 is operating in the Central role.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)
        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GAP_CONN_DCON_1(self):
        """
        Verify the IUT1 in the Directed Connectable Mode can connect with another
        device performing the General Connection Establishment Procedure.

        The IUT1 is operating in the Peripheral role.
        """

        connection_procedure(self, central=self.iut2, peripheral=self.iut1)

        iut_addr = self.iut1.stack.gap.iut_addr_get()
        iut2_addr = self.iut2.stack.gap.iut_addr_get()

        def verify_iut1(args):
            return verify_address(args, iut2_addr)

        def verify_iut2(args):
            return verify_address(args, iut_addr)

        future_iut1 = btp.gap_sec_level_changed_ev(self.iut1, verify_iut1)
        future_iut2 = btp.gap_sec_level_changed_ev(self.iut2, verify_iut2)

        btp.gap_pair(self.iut1, self.iut2.stack.gap.iut_addr_get())

        wait_futures([future_iut1, future_iut2], timeout=EV_TIMEOUT)

        disconnection_procedure(self, central=self.iut2, peripheral=self.iut1)

        btp.gap_start_direct_adv(self.iut1, self.iut2.stack.gap.iut_addr_get())

        def verify_central(args):
            return verify_address(args, self.iut1.stack.gap.iut_addr_get())

        future_central = btp.gap_connected_ev(self.iut2, verify_central)
        future_peripheral = btp.gap_connected_ev(self.iut1)

        btp.gap_conn(self.iut2, self.iut1.stack.gap.iut_addr_get())

        wait_futures([future_central, future_peripheral], timeout=EV_TIMEOUT)

        self.assertTrue(self.iut2.stack.gap.is_connected())
        self.assertTrue(self.iut1.stack.gap.is_connected())

        disconnection_procedure(self, central=self.iut2, peripheral=self.iut1)

    def test_btp_GAP_CONN_CPUP_1(self):
        """
        Verify the IUT1 can perform the Connection Parameter Update Procedure
        using valid parameters for the peer device; the peer device accepts
        the updated connection parameters.

        The IUT1 is operating in the Peripheral role and is the initiator
        performing the Connection Parameter Update Procedure; the IUT2
        is operating in the Central role and is the responder.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        conn_params = self.iut1.stack.gap.get_conn_params()
        iut_addr = self.iut1.stack.gap.iut_addr_get()
        iut2_addr = self.iut2.stack.gap.iut_addr_get()

        conn_itvl_min, conn_itvl_max, latency, supervision_timeout = (
            conn_params.conn_itvl,
            conn_params.conn_itvl,
            conn_params.conn_latency + 2,
            conn_params.supervision_timeout)

        btp.gap_conn_param_update(self.iut2,
                                  self.iut1.stack.gap.iut_addr_get(),
                                  conn_itvl_min, conn_itvl_max, latency,
                                  supervision_timeout)

        def verify_iut1(args):
            return verify_conn_params(args, iut2_addr, conn_itvl_min,
                                      conn_itvl_max, latency,
                                      supervision_timeout)

        def verify_iut2(args):
            return verify_conn_params(args, iut_addr, conn_itvl_min,
                                      conn_itvl_max, latency,
                                      supervision_timeout)

        wait_futures([btp.gap_conn_param_update_ev(self.iut1, verify_iut1),
                      btp.gap_conn_param_update_ev(self.iut2, verify_iut2)],
                     timeout=EV_TIMEOUT)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GAP_CONN_CPUP_2(self):
        """
        Verify the IUT1 can perform the Connection Parameter Update Procedure
        using valid parameters for the peer device; the peer device accepts
        the updated connection parameters.

        The IUT1 is operating in the Central role and is the initiator performing
        the Connection Parameter Update Procedure and the IUT2 is
        operating in the Peripheral role and is the responder.
        """

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        conn_params = self.iut1.stack.gap.get_conn_params()
        iut_addr = self.iut1.stack.gap.iut_addr_get()
        iut2_addr = self.iut2.stack.gap.iut_addr_get()

        conn_itvl_min, conn_itvl_max, latency, supervision_timeout = (
            conn_params.conn_itvl,
            conn_params.conn_itvl,
            conn_params.conn_latency + 2,
            conn_params.supervision_timeout)

        btp.gap_conn_param_update(self.iut1,
                                  self.iut2.stack.gap.iut_addr_get(),
                                  conn_itvl_min, conn_itvl_max, latency,
                                  supervision_timeout)

        def verify_iut1(args):
            return verify_conn_params(args, iut2_addr, conn_itvl_min,
                                      conn_itvl_max, latency,
                                      supervision_timeout)

        def verify_iut2(args):
            return verify_conn_params(args, iut_addr, conn_itvl_min,
                                      conn_itvl_max, latency,
                                      supervision_timeout)

        wait_futures([btp.gap_conn_param_update_ev(self.iut1, verify_iut1),
                      btp.gap_conn_param_update_ev(self.iut2, verify_iut2)],
                     timeout=EV_TIMEOUT)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GAP_CONN_PAIR_1(self):
        """
        Verify the IUT1 can perform the unauthenticated pairing procedure
        (Just Works) as the initiator.

        The IUT1 is operating in the Central role and is the initiator
        performing the pairing procedure; the IUT2
        is operating in the Peripheral role and is the responder.
        """

        btp.gap_set_io_cap(self.iut2, IOCap.no_input_output)
        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        iut_addr = self.iut1.stack.gap.iut_addr_get()
        iut2_addr = self.iut2.stack.gap.iut_addr_get()

        def verify_iut1(args):
            return verify_address(args, iut2_addr)

        def verify_iut2(args):
            return verify_address(args, iut_addr)

        future_iut1 = btp.gap_sec_level_changed_ev(self.iut1, verify_iut1)
        future_iut2 = btp.gap_sec_level_changed_ev(self.iut2, verify_iut2)

        btp.gap_pair(self.iut1, self.iut2.stack.gap.iut_addr_get())

        wait_futures([future_iut1, future_iut2], timeout=EV_TIMEOUT)

        _, level = future_iut1.result()
        self.assertEqual(level, 1)

        _, level = future_iut2.result()
        self.assertEqual(level, 1)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GAP_CONN_PAIR_2(self):
        """
        Verify the IUT1 can perform the authenticated pairing procedure
        (Numeric Comparison) as the initiator.

        The IUT1 is operating in the Central role and is the initiator
        performing the pairing procedure; the IUT2
        is operating in the Peripheral role and is the responder.
        """

        btp.gap_set_io_cap(self.iut1, IOCap.display_yesno)
        btp.gap_set_io_cap(self.iut2, IOCap.display_yesno)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gap_pair(self.iut1, self.iut2.stack.gap.iut_addr_get())

        iut_addr = self.iut1.stack.gap.iut_addr_get()
        iut2_addr = self.iut2.stack.gap.iut_addr_get()

        def verify_master(args): return verify_address(args, iut2_addr)

        def verify_slave(args): return verify_address(args, iut_addr)

        future_master = btp.gap_passkey_confirm_req_ev(self.iut1, verify_master)
        future_slave = btp.gap_passkey_confirm_req_ev(self.iut2, verify_slave)

        wait_futures([future_master, future_slave], timeout=EV_TIMEOUT)

        results_master = future_master.result()
        results_slave = future_slave.result()

        pk_iut1 = results_master[1]
        self.assertIsNotNone(pk_iut1)
        pk_iut2 = results_slave[1]
        self.assertIsNotNone(pk_iut2)
        self.assertEqual(pk_iut1, pk_iut2)

        btp.gap_passkey_confirm(self.iut1,
                                self.iut2.stack.gap.iut_addr_get(), 1)

        btp.gap_passkey_confirm(self.iut2,
                                self.iut1.stack.gap.iut_addr_get(), 1)

        future_master = btp.gap_sec_level_changed_ev(self.iut1, verify_master)
        future_slave = btp.gap_sec_level_changed_ev(self.iut2, verify_slave)

        wait_futures([future_master, future_slave], timeout=EV_TIMEOUT)

        _, level = future_master.result()
        self.assertEqual(level, 3)

        _, level = future_slave.result()
        self.assertEqual(level, 3)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

    def test_btp_GAP_CONN_PAIR_3(self):
        """
        Verify the IUT1 can perform the authenticated pairing procedure
        (Keyboard Input) as the initiator.

        The IUT1 is operating in the Central role and is the initiator
        performing the pairing procedure; the IUT2
        is operating in the Peripheral role and is the responder.
        """

        btp.gap_set_io_cap(self.iut1, IOCap.keyboard_only)
        btp.gap_set_io_cap(self.iut2, IOCap.display_only)

        connection_procedure(self, central=self.iut1, peripheral=self.iut2)

        btp.gap_pair(self.iut1,
                     self.iut2.stack.gap.iut_addr_get())

        iut_addr = self.iut1.stack.gap.iut_addr_get()
        iut2_addr = self.iut2.stack.gap.iut_addr_get()

        def verify_master(args): return verify_address(args, iut2_addr)

        def verify_slave(args): return verify_address(args, iut_addr)

        future_slave = btp.gap_passkey_disp_ev(self.iut2, verify_slave)
        future_master = btp.gap_passkey_entry_req_ev(self.iut1, verify_master)

        wait_futures([future_master, future_slave], timeout=EV_TIMEOUT)
        results_slave = future_slave.result()
        pk_iut2 = results_slave[1]
        self.assertIsNotNone(pk_iut2)

        btp.gap_passkey_entry_rsp(self.iut1, iut2_addr, pk_iut2)

        future_master = btp.gap_sec_level_changed_ev(self.iut1, verify_master)
        future_slave = btp.gap_sec_level_changed_ev(self.iut2, verify_slave)

        wait_futures([future_master, future_slave], timeout=EV_TIMEOUT)

        _, level = future_master.result()
        self.assertEqual(level, 3)

        _, level = future_slave.result()
        self.assertEqual(level, 3)

        disconnection_procedure(self, central=self.iut1, peripheral=self.iut2)

