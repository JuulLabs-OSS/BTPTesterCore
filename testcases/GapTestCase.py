import os

from pybtp import btp
from pybtp.types import AdType, IOCap
from pybtp.utils import wait_futures
from testcases.BTPTestCase import BTPTestCase
from testcases.utils import preconditions, find_adv_by_uuid, EV_TIMEOUT, \
    connection_procedure, disconnection_procedure, verify_address, \
    verify_conn_params


class GapTestCase(BTPTestCase):
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

        uuid = os.urandom(2)
        btp.gap_adv_ind_on(self.lt, ad=[(AdType.uuid16_some, uuid)])

        def verify_f(args):
            return find_adv_by_uuid(args, btp.btp2uuid(len(uuid), uuid))

        btp.gap_start_discov(self.iut)
        future = btp.gap_device_found_ev(self.iut, verify_f)
        wait_futures([future], timeout=EV_TIMEOUT)
        btp.gap_stop_discov(self.iut)

        found = future.result()
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

