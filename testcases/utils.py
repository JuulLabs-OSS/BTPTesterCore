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

import logging
import os

from pybtp import btp
from pybtp.btp import parse_ad, ad_find_uuid16
from pybtp.types import AdType
from pybtp.utils import wait_futures
from stack.gap import BleAddress

EV_TIMEOUT = 20


def preconditions(iutctl):
    btp.core_reg_svc_gap(iutctl)
    btp.core_reg_svc_gatt(iutctl)
    iutctl.stack.gap_init()
    iutctl.stack.gatt_init()
    btp.gap_read_ctrl_info(iutctl)


def find_adv_by_addr(args, addr: BleAddress):
    le_adv = args
    logging.debug("matching %r %r", le_adv.addr, addr)
    return le_adv.addr == addr


def find_adv_by_uuid(args, uuid):
    le_adv = args
    logging.debug("matching %r", le_adv)
    try:
        ad = parse_ad(le_adv.eir)
    except Exception:
        return False
    uuids = ad_find_uuid16(ad)

    return uuid in uuids


def verify_conn_params(args, addr: BleAddress,
                       conn_itvl_min, conn_itvl_max,
                       conn_latency, supervision_timeout):
    params = args[1]
    return verify_address(args, addr) and \
           (params.conn_itvl >= conn_itvl_min) and \
           (params.conn_itvl <= conn_itvl_max) and \
           (params.conn_latency == conn_latency) and \
           (params.supervision_timeout == supervision_timeout)


def verify_address(args, addr: BleAddress):
    peer_addr = args[0]
    return peer_addr == addr


def verify_value_changed_ev(args, handle, value):
    return args[0] == handle and args[1] == value


def verify_notification_ev(args, addr: BleAddress, type, handle):
    logging.debug("%r %r %r %r", args, addr, type, handle)
    return args[0] == addr and args[1] == type and \
           args[2] == handle


def connection_procedure(testcase, central, peripheral):
    btp.gap_set_conn(peripheral)
    btp.gap_set_gendiscov(peripheral)

    uuid = os.urandom(2)
    btp.gap_adv_ind_on(peripheral, ad=[(AdType.uuid16_some, uuid)])

    def verify_f(args): return find_adv_by_uuid(args,
                                                btp.btp2uuid(len(uuid), uuid))

    btp.gap_start_discov(central)
    future = btp.gap_device_found_ev(central, verify_f)
    wait_futures([future], timeout=EV_TIMEOUT)
    btp.gap_stop_discov(central)

    found = future.result()

    testcase.assertIsNotNone(found)
    peripheral.stack.gap.iut_addr_set(found.addr)

    def verify_central(args): return verify_address(args, found.addr)

    future_central = btp.gap_connected_ev(central, verify_central)
    future_peripheral = btp.gap_connected_ev(peripheral)

    btp.gap_conn(central, peripheral.stack.gap.iut_addr_get())

    wait_futures([future_central, future_peripheral], timeout=EV_TIMEOUT)

    testcase.assertTrue(central.stack.gap.is_connected())
    testcase.assertTrue(peripheral.stack.gap.is_connected())

    central_addr, _ = future_peripheral.result()
    central.stack.gap.iut_addr_set(central_addr)


def disconnection_procedure(testcase, central, peripheral):
    periph_addr = peripheral.stack.gap.iut_addr_get()

    def verify_central(args):
        return verify_address(args, periph_addr)

    future_central = btp.gap_disconnected_ev(central, verify_central)
    future_peripheral = btp.gap_disconnected_ev(peripheral)

    btp.gap_disconn(central, peripheral.stack.gap.iut_addr_get())

    wait_futures([future_central, future_peripheral], timeout=EV_TIMEOUT)

    testcase.assertFalse(peripheral.stack.gap.is_connected())
    testcase.assertFalse(central.stack.gap.is_connected())


