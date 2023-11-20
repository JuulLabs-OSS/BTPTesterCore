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
import argparse
import logging
import unittest
import sys
import time

from common.board import NordicBoard
from projects.android.iutctl import AndroidCtl
from projects.mynewt.iutctl import MynewtCtl
from testcases.GattTestCase import GattTestCase
from testcases.GapTestCase import GapTestCase


def main():
    parser = argparse.ArgumentParser(description='BTP End-to-end tester')
    parser.add_argument('--test', type=str, action='append',
                        help='Specific test to run. Can be class or ' \
                             '[class]#[test] e.g. GattTestCase#test_btp_GATT_CL_GAR_4')
    parser.add_argument('--use-Mynewt', action='store_true',
                        help='Will use Mynewt as Central and Peripheral devices. ' \
                             'If an --android device is specified, it will use both')
    parser.add_argument('--android-central', type=str,
                        help='Central Android device serial number')
    parser.add_argument('--android-peripheral', type=str,
                        help='Peripheral Android device serial number')
    parser.add_argument('--run-count', type=int, default=1,
                        help='Run the tests again after completion')
    parser.add_argument('--rerun-until-failure', action='store_true',
                        help='Run the tests again after completion until one test fails')
    parser.add_argument('--fail-fast', action='store_true',
                        help='Stops the run at first failure')
    _ = parser.parse_args()

    format = ("%(asctime)s %(levelname)s %(threadName)-20s "
              "%(filename)-25s %(lineno)-5s %(funcName)-25s : %(message)s")
    logging.basicConfig(level=logging.DEBUG,
                        filename='logger_traces.log',
                        format=format)
    logger = logging.getLogger('websockets.server')
    logger.setLevel(logging.ERROR)
    logger.addHandler(logging.StreamHandler())

    if _.use_nordic and _.android_central is None and _.android_peripheral is None:
        central = MynewtCtl(NordicBoard())
        peripheral = MynewtCtl(NordicBoard())
    elif _.use_nordic:
        if _.android_central is not None:
            central = AndroidCtl(_.android_central)
            peripheral = MynewtCtl(NordicBoard())
        else:
            central = MynewtCtl(NordicBoard())
            peripheral = AndroidCtl(_.android_peripheral)
    else:
        central, peripheral = AndroidCtl.from_serials_or_auto(_.android_central,
                                                              _.android_peripheral)

    def create_suite():
        suite = unittest.TestSuite()
        if _.test is not None:
            for arg in _.test:
                test = arg.split('#')
                if len(test) > 1:
                    suite.addTest(eval(test[0])(test[1],
                                    central, peripheral))
                else:
                    suite.addTests(eval(test[0]).init_testcases(central, peripheral))
        if _.test is None:
            suite.addTests(GapTestCase.init_testcases(central, peripheral))
            suite.addTests(GattTestCase.init_testcases(central, peripheral))
        return suite

    runner = unittest.TextTestRunner(verbosity=2, failfast=_.fail_fast)

    suite = create_suite();

    print("Starting tester" \
          + ", runs: " + ("until failure" if _.rerun_until_failure else str(_.run_count)) \
          + ", fail-fast: " + str(_.fail_fast))
    print("Central IUT: " + str(central))
    print("Peripheral IUT: " + str(peripheral))

    run_count = 0
    run_failed = False
    results = []
    while run_count < _.run_count or (_.rerun_until_failure and not run_failed):
        suite = create_suite();
        print("\n### Starting run " + str(run_count + 1) + "/" \
              + str(_.run_count) + " with " + str(suite.countTestCases()) + " tests ###\n")
        result = runner.run(suite)
        results.append(result)
        run_failed = len(result.errors) + len(result.failures) > 0
        if _.fail_fast and run_failed:
            break
        run_count += 1
        time.sleep(1)

if __name__ == "__main__":
    main()
