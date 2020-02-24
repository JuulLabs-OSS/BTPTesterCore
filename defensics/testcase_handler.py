from pybtp import btp, defs
from pybtp.types import BTPErrorInvalidStatus, IOCap
from pybtp.utils import wait_futures
from stack.gatt import GattDB
from testcases.utils import preconditions, EV_TIMEOUT, find_adv_by_addr


class TestCaseHandler:
    def __init__(self, config):
        self.config = config

    def test_case_setup(self, iut):
        iut.wait_iut_ready_event()
        preconditions(iut)

    def test_case_check_health(self, iut):
        btp.gap_read_ctrl_info(iut)

    def test_case_teardown(self, iut):
        pass

    def test_ATT_Server(self, iut, valid):
        btp.gap_set_conn(iut)
        btp.gap_set_gendiscov(iut)
        btp.gap_adv_ind_on(iut)

    def test_ATT_Client_Exchange_MTU(self, iut, valid):
        btp.gap_conn(iut, self.config.tester_addr)
        btp.gap_wait_for_connection(iut)
        btp.gattc_exchange_mtu(iut, self.config.tester_addr)
        tuple_hdr, tuple_data = iut.btp_worker.read()
        try:
            btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                              defs.GATT_EXCHANGE_MTU)
        except BTPErrorInvalidStatus:
            pass

    def test_ATT_Client_Discover_Primary_Services(self, iut, valid):
        btp.gap_conn(iut, self.config.tester_addr)
        btp.gap_wait_for_connection(iut)

        btp.gattc_disc_prim_svcs(iut, self.config.tester_addr)
        tuple_hdr, tuple_data = iut.btp_worker.read()
        try:
            btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                              defs.GATT_DISC_PRIM_SVCS)
        except BTPErrorInvalidStatus:
            pass

        try:
            # In some test cases Defensics won't disconnect
            # so we have to try to disconnect ourselves
            btp.gap_disconn(iut, self.config.tester_addr)
        except BTPErrorInvalidStatus:
            pass

    def test_ATT_Client_Discover_Service_by_uuid(self, iut, valid):
        btp.gap_conn(iut, self.config.tester_addr)
        btp.gap_wait_for_connection(iut)

        btp.gattc_disc_prim_uuid(iut, self.config.tester_addr, self.config.tester_service_uuid)
        tuple_hdr, tuple_data = iut.btp_worker.read()
        try:
            btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                              defs.GATT_DISC_PRIM_UUID)
        except BTPErrorInvalidStatus:
            pass

    def test_ATT_Client_Discover_All_Characteristics(self, iut, valid):
        btp.gap_conn(iut, self.config.tester_addr)
        btp.gap_wait_for_connection(iut)

        btp.gattc_disc_all_chrc(iut, self.config.tester_addr, start_hdl=1, stop_hdl=0xffff)
        tuple_hdr, tuple_data = iut.btp_worker.read()
        try:
            btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                              defs.GATT_DISC_ALL_CHRC)
        except BTPErrorInvalidStatus:
            pass

    def test_ATT_Client_Discover_Characteristic_Descriptors(self, iut, valid):
        btp.gap_conn(iut, self.config.tester_addr)
        btp.gap_wait_for_connection(iut)

        db = GattDB()
        btp.gattc_disc_prim_svcs(iut, self.config.tester_addr)
        btp.gattc_disc_prim_svcs_rsp(iut, db)

        for svc in db.get_services():
            start, end = svc.handle, svc.end_hdl

            btp.gattc_disc_all_chrc(iut, self.config.tester_addr, start, end)
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

            btp.gattc_disc_all_desc(iut, self.config.tester_addr, start_hdl, end_hdl)
            tuple_hdr, tuple_data = iut.btp_worker.read()
            try:
                btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                                  defs.GATT_DISC_ALL_DESC)
            except BTPErrorInvalidStatus:
                pass

    def test_ATT_Client_Read_Attribute_Value(self, iut, valid):
        btp.gap_conn(iut, self.config.tester_addr)
        btp.gap_wait_for_connection(iut)

        btp.gattc_read(iut, self.config.tester_addr, self.config.tester_read_hdl)
        tuple_hdr, tuple_data = iut.btp_worker.read()
        try:
            btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                              defs.GATT_READ)
        except BTPErrorInvalidStatus:
            pass

    def test_ATT_Client_Read_Long_Attribute_Value(self, iut, valid):
        btp.gap_conn(iut, self.config.tester_addr)
        btp.gap_wait_for_connection(iut)

        btp.gattc_read_long(iut, self.config.tester_addr, self.config.tester_read_hdl, 0)
        tuple_hdr, tuple_data = iut.btp_worker.read()
        try:
            btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                              defs.GATT_READ_LONG)
        except BTPErrorInvalidStatus:
            pass

        try:
            # In some test cases Defensics won't disconnect
            # so we have to try to disconnect ourselves
            btp.gap_disconn(iut, self.config.tester_addr)
        except BTPErrorInvalidStatus:
            pass

    def test_ATT_Client_Write_Attribute_Value(self, iut, valid):
        btp.gap_conn(iut, self.config.tester_addr)
        btp.gap_wait_for_connection(iut)

        btp.gattc_write(iut, self.config.tester_addr, self.config.tester_write_hdl, '00')
        tuple_hdr, tuple_data = iut.btp_worker.read()
        try:
            btp.btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                              defs.GATT_WRITE)
        except BTPErrorInvalidStatus:
            pass

    def test_SMP_Server_SC_Just_Works(self, iut, valid):
        btp.gap_set_io_cap(iut, IOCap.keyboard_display)
        btp.gap_set_conn(iut)
        btp.gap_set_gendiscov(iut)
        btp.gap_adv_ind_on(iut)

    def test_SMP_Server_SC_Numeric_Comparison(self, iut, valid):
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
            btp.gap_passkey_confirm(iut, self.config.tester_addr, 1)
        except (TimeoutError, BTPErrorInvalidStatus) as e:
            if valid:
                raise e

    def test_SMP_Server_SC_Passkey_Entry(self, iut, valid):
        btp.gap_set_io_cap(iut, IOCap.keyboard_display)
        btp.gap_set_conn(iut)
        btp.gap_set_gendiscov(iut)
        btp.gap_adv_ind_on(iut)

        future = btp.gap_passkey_entry_req_ev(iut)
        try:
            wait_futures([future], timeout=EV_TIMEOUT)
            btp.gap_passkey_entry_rsp(iut, self.config.tester_addr, self.config.tester_passkey)
        except (TimeoutError, BTPErrorInvalidStatus) as e:
            if valid:
                raise e

    def test_SMP_Client_SC_Just_Works(self, iut, valid):
        btp.gap_set_io_cap(iut, IOCap.keyboard_display)
        btp.gap_conn(iut, self.config.tester_addr)
        btp.gap_wait_for_connection(iut)

    def test_SMP_Client_SC_Numeric_Comparison(self, iut, valid):
        btp.gap_set_io_cap(iut, IOCap.keyboard_display)
        btp.gap_conn(iut, self.config.tester_addr)
        btp.gap_wait_for_connection(iut)

        future = btp.gap_passkey_confirm_req_ev(iut)
        try:
            wait_futures([future], timeout=EV_TIMEOUT)
            results = future.result()
            pk_iut = results[1]
            assert (pk_iut is not None)
            btp.gap_passkey_confirm(iut, self.config.tester_addr, 1)
        except (TimeoutError, BTPErrorInvalidStatus) as e:
            if valid:
                raise e

    def test_SMP_Client_SC_Passkey_Entry(self, iut, valid):
        btp.gap_set_io_cap(iut, IOCap.keyboard_display)
        btp.gap_conn(iut, self.config.tester_addr)
        btp.gap_wait_for_connection(iut)

        future = btp.gap_passkey_entry_req_ev(iut)
        try:
            wait_futures([future], timeout=EV_TIMEOUT)
            btp.gap_passkey_entry_rsp(iut, self.config.tester_addr, self.config.tester_passkey)
        except (TimeoutError, BTPErrorInvalidStatus) as e:
            if valid:
                raise e

    def test_Advertising_Data(self, iut, valid):
        def verify_f(args):
            return find_adv_by_addr(args, self.config.tester_addr)

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

    def get_before_case_handler(self, key):
        try:
            return next(v for k, v in self.before_case_handlers.items() if key.startswith(k))
        except StopIteration:
            return None
