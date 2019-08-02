import unittest


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


