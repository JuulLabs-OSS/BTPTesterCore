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

from testcases.BTPTestCaseLT2 import BTPTestCaseLT2
from testcases.utils import preconditions, connection_procedure, \
    disconnection_procedure


class GapTestCaseLT2(BTPTestCaseLT2):
    def __init__(self, testname, iut, lt1, lt2):
        super(__class__, self).__init__(testname, iut, lt1, lt2)

    def setUp(self):
        super(__class__, self).setUp()
        preconditions(self.iut)
        preconditions(self.lt1)
        preconditions(self.lt2)

    def tearDown(self):
        super(__class__, self).tearDown()

    def test_advertising(self):
        connection_procedure(self, central=self.lt1, peripheral=self.iut)
        connection_procedure(self, central=self.lt2, peripheral=self.iut)

        disconnection_procedure(self, central=self.lt1, peripheral=self.iut)
        disconnection_procedure(self, central=self.lt2, peripheral=self.iut)

    def test_connection(self):
        connection_procedure(self, central=self.iut, peripheral=self.lt1)
        connection_procedure(self, central=self.iut, peripheral=self.lt2)

        disconnection_procedure(self, central=self.iut, peripheral=self.lt1)
        disconnection_procedure(self, central=self.iut, peripheral=self.lt2)
