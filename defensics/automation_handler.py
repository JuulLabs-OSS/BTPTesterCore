from pybtp import btp
from stack.gap import BleAddress
from testcases.utils import preconditions

TESTER_ADDR = BleAddress('00:1b:dc:06:9e:49', 0)
TESTER_READ_HDL = '0x0003'
TESTER_WRITE_HDL = '0x0005'


def test_ATT_Client_Discover_Services(iut):
    btp.gap_conn(iut, TESTER_ADDR)


test_handler = {
    'ATT.Discover-primary-services': test_ATT_Client_Discover_Services,
}


class AutomationHandler:
    def __init__(self, iut):
        if iut is None:
            raise Exception("IUT1 is None")
        self.iut = iut

    def process(self, instrumentation_step, params, rsp_hdl):
        if not str.startswith(instrumentation_step, '/before-case'):
            return

        # test_group = params['CODE_TEST_GROUP']

        self.setUp()
        test_ATT_Client_Discover_Services(self.iut)

    def setUp(self):
        self.iut.start()
        self.iut.wait_iut_ready_event()
        preconditions(self.iut)
