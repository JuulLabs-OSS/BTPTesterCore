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

import unittest


class BTPTestCase(unittest.TestCase):
    def __init__(self, testname, iut1, iut2):
        super(__class__, self).__init__(testname)

        if iut1 is None:
            raise Exception("IUT1 is None")

        if iut2 is None:
            raise Exception("IUT2 is None")

        self.iut1 = iut1
        self.iut2 = iut2

    @classmethod
    def init_testcases(cls, iut1, iut2):
        testcases = []
        ldr = unittest.TestLoader()
        for testname in ldr.getTestCaseNames(cls):
            testcases.append(cls(testname, iut1, iut2))
        return testcases

    def setUp(self):
        self.iut1.start()
        self.iut1.wait_iut_ready_event()
        self.iut2.start()
        self.iut2.wait_iut_ready_event()

    def tearDown(self):
        self.iut1.stop()
        self.iut2.stop()


