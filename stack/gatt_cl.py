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
from stack.common import wait_for_event
from stack.gatt import GattDB


def is_procedure_done(list, cnt):
    if cnt is None:
        return False

    if cnt <= 0:
        return True

    return len(list) == cnt


class GattCl:
    def __init__(self):
        self.db = GattDB()
        self.verify_values = []
        self.prim_svcs_cnt = None
        self.prim_svcs = []
        self.incl_svcs_cnt = None
        self.incl_svcs = []
        self.chrcs_cnt = None
        self.chrcs = []
        self.dscs_cnt = None
        self.dscs = []
        self.notifications = []
        self.write_status = None
        self.event_to_await = None

    def set_event_to_await(self, event):
        self.event_to_await = event

    def wait_for_rsp_event(self, timeout=30):
        return wait_for_event(timeout, self.event_to_await)

    def is_prim_disc_complete(self, *args):
        return is_procedure_done(self.prim_svcs, self.prim_svcs_cnt)

    def is_incl_disc_complete(self, *args):
        return is_procedure_done(self.incl_svcs, self.incl_svcs_cnt)

    def wait_for_prim_svcs(self, timeout=20):
        return wait_for_event(timeout, self.is_prim_disc_complete)

    def wait_for_incl_svcs(self, timeout=30):
        return wait_for_event(timeout, self.is_incl_disc_complete)

    def is_chrcs_disc_complete(self, *args):
        return is_procedure_done(self.chrcs, self.chrcs_cnt)

    def wait_for_chrcs(self, timeout=30):
        return wait_for_event(timeout, self.is_chrcs_disc_complete)

    def is_dscs_disc_complete(self, *args):
        return is_procedure_done(self.dscs, self.dscs_cnt)

    def wait_for_descs(self, timeout=30):
        return wait_for_event(timeout, self.is_dscs_disc_complete)

    def is_read_complete(self, *args):
        return self.verify_values != []

    def wait_for_read(self, timeout=30):
        return wait_for_event(timeout, self.is_read_complete)

    def is_write_completed(self, *args):
        return self.write_status is not None

    def wait_for_write_rsp(self, timeout=30):
        return wait_for_event(timeout, self.is_write_completed)

    def is_notification_rxed(self, expected_count):
        if expected_count > 0:
            return len(self.notifications) == expected_count
        return len(self.notifications) > 0

    def wait_for_notifications(self, timeout=30, expected_count=0):
        return wait_for_event(timeout,
                              self.is_notification_rxed, expected_count)
