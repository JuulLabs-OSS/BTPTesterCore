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
import signal
import sys
import time

from common.board import NordicBoard
from common.iutctl import IutCtl
from projects.android.iutctl import AndroidCtl
from projects.mynewt.iutctl import MynewtCtl
from testcases.GattTestCase import GattTestCase
from testcases.GapTestCase import GapTestCase


def main():
    parser = argparse.ArgumentParser(description='BTP End-to-end tester')
    parser.add_argument('--test', type=str, action='append',
                        help='Specific test to run. Can be class or ' \
                             '[class]#[test] e.g. GattTestCase#test_btp_GATT_CL_GAR_4')

    parser.add_argument('--central', type=str, nargs=2, \
                        metavar=('OS', 'serial number'), required=True, \
                        help='OS and serial number for central IUT')
    parser.add_argument('--peripheral', type=str, nargs=2, \
                        metavar=('OS', 'serial number'), required=True, \
                        help='OS and serial number for peripheral IUT')

    parser.add_argument('--flash-central', type=str, nargs=2, \
                        metavar=('board name', 'project path'), \
                        help='Build the OS specified in --central and flash the board')
    parser.add_argument('--flash-peripheral', type=str, nargs=2, \
                        metavar=('board name', 'project path'), \
                        help='Build the OS specified in --peripheral and flash the board')

    parser.add_argument('--run-count', type=int, default=1,
                        help='Run the tests again after completion')
    parser.add_argument('--rerun-until-failure', action='store_true',
                        help='Run the tests again after completion until one test fails')
    parser.add_argument('--fail-fast', action='store_true',
                        help='Stops the run at first failure')
    args = parser.parse_args()

    format = ("%(asctime)s %(levelname)s %(threadName)-20s "
              "%(filename)-25s %(lineno)-5s %(funcName)-25s : %(message)s")
    logging.basicConfig(level=logging.DEBUG,
                        filename='logger_traces.log',
                        format=format)
    logger = logging.getLogger('websockets.server')
    logger.setLevel(logging.ERROR)
    logger.addHandler(logging.StreamHandler())

    central_os, central_sn = args.central
    peripheral_os, peripheral_sn = args.peripheral

    if central_os == IutCtl.TYPE_MYNEWT:
        central = MynewtCtl(NordicBoard(central_sn))
    elif central_os == IutCtl.TYPE_ANDROID:
        central = AndroidCtl(central_sn)
    else:
        raise ValueError("Central OS is not implemented.")

    if peripheral_os == IutCtl.TYPE_MYNEWT:
        peripheral = MynewtCtl(NordicBoard(peripheral_sn))
    elif peripheral_os == IutCtl.TYPE_ANDROID:
        peripheral = AndroidCtl(peripheral_sn)
    else:
        raise ValueError("Peripheral OS is not implemented.")

    if args.flash_central is not None:
        board_name, project_path = args.flash_central
        central.build_and_flash(board_name, project_path)
    if args.flash_peripheral is not None:
        board_name, project_path = args.flash_peripheral
        peripheral.build_and_flash(board_name, project_path)

    def create_suite():
        suite = unittest.TestSuite()
        if args.test is not None:
            for arg in args.test:
                test = arg.split('#')
                if len(test) > 1:
                    suite.addTest(eval(test[0])(test[1],
                                    central, peripheral))
                else:
                    suite.addTests(eval(test[0]).init_testcases(central, peripheral))
        if args.test is None:
            suite.addTests(GapTestCase.init_testcases(central, peripheral))
            suite.addTests(GattTestCase.init_testcases(central, peripheral))
        return suite

    runner = unittest.TextTestRunner(verbosity=2, failfast=args.fail_fast)

    suite = create_suite();

    print("Starting tester" \
          + ", runs: " + ("until failure" if args.rerun_until_failure else str(args.run_count)) \
          + ", fail-fast: " + str(args.fail_fast))
    print("Central IUT: " + str(central))
    print("Peripheral IUT: " + str(peripheral))

    run_count = 0
    run_failed = False
    results = []
    while run_count < args.run_count or (args.rerun_until_failure and not run_failed):
        suite = create_suite();
        print("\n### Starting run " + str(run_count + 1) + "/" \
              + str(args.run_count) + " with " + str(suite.countTestCases()) + " tests ###\n")
        result = runner.run(suite)
        results.append(result)
        run_failed = len(result.errors) + len(result.failures) > 0
        if args.fail_fast and run_failed:
            break
        run_count += 1
        time.sleep(1)

if __name__ == "__main__":
    def sigint_handler(sig, frame):
        """Thread safe SIGINT interrupting"""
        set_global_end()

        if sys.platform != "win32":
            signal.signal(signal.SIGINT, prev_sigint_handler)
            threading.Thread(target=signal.raise_signal(signal.SIGINT)).start()

    try:
        prev_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, sigint_handler)

        rc = main()
    except KeyboardInterrupt:  # Ctrl-C
        rc = 14
    except SystemExit:
        raise
    except BaseException as e:
        logging.exception(e)
        import traceback

        traceback.print_exc()
        rc = 16
    finally:
        sys.exit(rc)
