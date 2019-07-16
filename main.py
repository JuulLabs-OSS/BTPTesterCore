import logging
import unittest

from projects.android.iutctl import AndroidCtl
from projects.mynewt.iutctl import MynewtCtl
from pybtp.testcase import GAPTestCase


def main():
    print("Starting tester")
    format = ("%(asctime)s %(name)-20s %(levelname)s %(threadName)-20s "
              "%(filename)-25s %(lineno)-5s %(funcName)-25s : %(message)s")
    logging.basicConfig(level=logging.DEBUG,
                        format=format)
    logger = logging.getLogger('websockets.server')
    logger.setLevel(logging.ERROR)
    logger.addHandler(logging.StreamHandler())

    mynewt1 = MynewtCtl('/dev/ttyACM0', '683357425')
    mynewt2 = MynewtCtl('/dev/ttyACM1', '683802616')
    # android = AndroidCtl('192.168.9.123', 8765)

    def suite():
        suite = unittest.TestSuite()
        # suite.addTest(GAPTestCase('test_connection_parameter_update_master',
        #                           mynewt1, android))
        suite.addTests(GAPTestCase.init_testcases(mynewt1, mynewt2))
        # suite.addTests(GAPTestCase.init_testcases(mynewt1, android))
        return suite

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())


if __name__ == "__main__":
    main()
