#
# auto-pts - The Bluetooth PTS Automation Framework
#
# Copyright (c) 2017, Intel Corporation.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#

"""Wrapper around btp messages. The functions are added as needed."""

import binascii
import logging
import struct
import uuid

from common.iutctl import IutCtl
from pybtp import defs
from stack.gap import LeAdv, BleAddress, ConnParams
from stack.gatt import GattDB, GattPrimary, GattSecondary, GattCharacteristic, \
    GattServiceIncluded, GattCharacteristicDescriptor
from .types import BTPError, gap_settings_btp2txt, Addr, UUID, AdType

CONTROLLER_INDEX = 0

CORE = {
    "gap_reg": (defs.BTP_SERVICE_ID_CORE, defs.CORE_REGISTER_SERVICE,
                defs.BTP_INDEX_NONE, defs.BTP_SERVICE_ID_GAP),
    "gap_unreg": (defs.BTP_SERVICE_ID_CORE, defs.CORE_UNREGISTER_SERVICE,
                  defs.BTP_INDEX_NONE, defs.BTP_SERVICE_ID_GAP),
    "gatt_reg": (defs.BTP_SERVICE_ID_CORE, defs.CORE_REGISTER_SERVICE,
                 defs.BTP_INDEX_NONE, defs.BTP_SERVICE_ID_GATT),
    "gatt_unreg": (defs.BTP_SERVICE_ID_CORE, defs.CORE_UNREGISTER_SERVICE,
                   defs.BTP_INDEX_NONE, defs.BTP_SERVICE_ID_GATT),
    "l2cap_reg": (defs.BTP_SERVICE_ID_CORE, defs.CORE_REGISTER_SERVICE,
                  defs.BTP_INDEX_NONE, defs.BTP_SERVICE_ID_L2CAP),
    "l2cap_unreg": (defs.BTP_SERVICE_ID_CORE, defs.CORE_UNREGISTER_SERVICE,
                    defs.BTP_INDEX_NONE, defs.BTP_SERVICE_ID_L2CAP),
    "mesh_reg": (defs.BTP_SERVICE_ID_CORE, defs.CORE_REGISTER_SERVICE,
                 defs.BTP_INDEX_NONE, defs.BTP_SERVICE_ID_MESH),
    "mesh_unreg": (defs.BTP_SERVICE_ID_CORE, defs.CORE_UNREGISTER_SERVICE,
                   defs.BTP_INDEX_NONE, defs.BTP_SERVICE_ID_MESH),
    "read_supp_cmds": (defs.BTP_SERVICE_ID_CORE,
                       defs.CORE_READ_SUPPORTED_COMMANDS,
                       defs.BTP_INDEX_NONE, ""),
    "read_supp_svcs": (defs.BTP_SERVICE_ID_CORE,
                       defs.CORE_READ_SUPPORTED_SERVICES,
                       defs.BTP_INDEX_NONE, ""),
}

GAP = {
    "start_adv": (defs.BTP_SERVICE_ID_GAP, defs.GAP_START_ADVERTISING,
                  CONTROLLER_INDEX),
    "stop_adv": (defs.BTP_SERVICE_ID_GAP, defs.GAP_STOP_ADVERTISING,
                 CONTROLLER_INDEX, ""),
    "conn": (defs.BTP_SERVICE_ID_GAP, defs.GAP_CONNECT, CONTROLLER_INDEX),
    "pair": (defs.BTP_SERVICE_ID_GAP, defs.GAP_PAIR, CONTROLLER_INDEX),
    "unpair": (defs.BTP_SERVICE_ID_GAP, defs.GAP_UNPAIR, CONTROLLER_INDEX),
    "disconn": (defs.BTP_SERVICE_ID_GAP, defs.GAP_DISCONNECT,
                CONTROLLER_INDEX),
    "set_io_cap": (defs.BTP_SERVICE_ID_GAP, defs.GAP_SET_IO_CAP,
                   CONTROLLER_INDEX),
    "set_conn": (defs.BTP_SERVICE_ID_GAP, defs.GAP_SET_CONNECTABLE,
                 CONTROLLER_INDEX, 1),
    "set_nonconn": (defs.BTP_SERVICE_ID_GAP, defs.GAP_SET_CONNECTABLE,
                    CONTROLLER_INDEX, 0),
    "set_nondiscov": (defs.BTP_SERVICE_ID_GAP, defs.GAP_SET_DISCOVERABLE,
                      CONTROLLER_INDEX, defs.GAP_NON_DISCOVERABLE),
    "set_gendiscov": (defs.BTP_SERVICE_ID_GAP, defs.GAP_SET_DISCOVERABLE,
                      CONTROLLER_INDEX, defs.GAP_GENERAL_DISCOVERABLE),
    "set_limdiscov": (defs.BTP_SERVICE_ID_GAP, defs.GAP_SET_DISCOVERABLE,
                      CONTROLLER_INDEX, defs.GAP_LIMITED_DISCOVERABLE),
    "set_powered_on": (defs.BTP_SERVICE_ID_GAP, defs.GAP_SET_POWERED,
                       CONTROLLER_INDEX, 1),
    "set_powered_off": (defs.BTP_SERVICE_ID_GAP, defs.GAP_SET_POWERED,
                        CONTROLLER_INDEX, 0),
    "start_discov": (defs.BTP_SERVICE_ID_GAP,
                     defs.GAP_START_DISCOVERY, CONTROLLER_INDEX),
    "stop_discov": (defs.BTP_SERVICE_ID_GAP, defs.GAP_STOP_DISCOVERY,
                    CONTROLLER_INDEX, ""),
    "read_ctrl_info": (defs.BTP_SERVICE_ID_GAP,
                       defs.GAP_READ_CONTROLLER_INFO,
                       CONTROLLER_INDEX, ""),
    "passkey_entry_rsp": (defs.BTP_SERVICE_ID_GAP,
                          defs.GAP_PASSKEY_ENTRY,
                          CONTROLLER_INDEX),
    "passkey_confirm": (defs.BTP_SERVICE_ID_GAP,
                        defs.GAP_PASSKEY_CONFIRM,
                        CONTROLLER_INDEX),
    "conn_param_update": (defs.BTP_SERVICE_ID_GAP,
                          defs.GAP_CONN_PARAM_UPDATE,
                          CONTROLLER_INDEX),
    "reset": (defs.BTP_SERVICE_ID_GAP, defs.GAP_RESET, CONTROLLER_INDEX, "")
}

GATTS = {
    "add_svc": (defs.BTP_SERVICE_ID_GATT, defs.GATT_ADD_SERVICE,
                CONTROLLER_INDEX),
    "start_server": (defs.BTP_SERVICE_ID_GATT, defs.GATT_START_SERVER,
                     CONTROLLER_INDEX, ""),
    "add_inc_svc": (defs.BTP_SERVICE_ID_GATT,
                    defs.GATT_ADD_INCLUDED_SERVICE, CONTROLLER_INDEX),
    "add_char": (defs.BTP_SERVICE_ID_GATT, defs.GATT_ADD_CHARACTERISTIC,
                 CONTROLLER_INDEX),
    "set_val": (defs.BTP_SERVICE_ID_GATT, defs.GATT_SET_VALUE,
                CONTROLLER_INDEX),
    "add_desc": (defs.BTP_SERVICE_ID_GATT, defs.GATT_ADD_DESCRIPTOR,
                 CONTROLLER_INDEX),
    "set_enc_key_size": (defs.BTP_SERVICE_ID_GATT,
                         defs.GATT_SET_ENC_KEY_SIZE, CONTROLLER_INDEX),
    "get_attrs": (defs.BTP_SERVICE_ID_GATT, defs.GATT_GET_ATTRIBUTES,
                  CONTROLLER_INDEX),
    "get_attr_val": (defs.BTP_SERVICE_ID_GATT,
                     defs.GATT_GET_ATTRIBUTE_VALUE, CONTROLLER_INDEX)
}

GATTC = {
    "exchange_mtu": (defs.BTP_SERVICE_ID_GATT, defs.GATT_EXCHANGE_MTU,
                     CONTROLLER_INDEX),
    "disc_prim_svcs": (defs.BTP_SERVICE_ID_GATT, defs.GATT_DISC_PRIM_SVCS,
                       CONTROLLER_INDEX),
    "disc_prim_uuid": (defs.BTP_SERVICE_ID_GATT, defs.GATT_DISC_PRIM_UUID,
                       CONTROLLER_INDEX),
    "find_included": (defs.BTP_SERVICE_ID_GATT, defs.GATT_FIND_INCLUDED,
                      CONTROLLER_INDEX),
    "disc_all_chrc": (defs.BTP_SERVICE_ID_GATT, defs.GATT_DISC_ALL_CHRC,
                      CONTROLLER_INDEX),
    "disc_chrc_uuid": (defs.BTP_SERVICE_ID_GATT, defs.GATT_DISC_CHRC_UUID,
                       CONTROLLER_INDEX),
    "disc_all_desc": (defs.BTP_SERVICE_ID_GATT, defs.GATT_DISC_ALL_DESC,
                      CONTROLLER_INDEX),
    "read": (defs.BTP_SERVICE_ID_GATT, defs.GATT_READ, CONTROLLER_INDEX),
    "read_long": (defs.BTP_SERVICE_ID_GATT, defs.GATT_READ_LONG,
                  CONTROLLER_INDEX),
    "read_multiple": (defs.BTP_SERVICE_ID_GATT, defs.GATT_READ_MULTIPLE,
                      CONTROLLER_INDEX),
    "write_without_rsp": (defs.BTP_SERVICE_ID_GATT,
                          defs.GATT_WRITE_WITHOUT_RSP, CONTROLLER_INDEX),
    "signed_write": (defs.BTP_SERVICE_ID_GATT,
                     defs.GATT_SIGNED_WRITE_WITHOUT_RSP, CONTROLLER_INDEX),
    "write": (defs.BTP_SERVICE_ID_GATT, defs.GATT_WRITE, CONTROLLER_INDEX),
    "write_long": (defs.BTP_SERVICE_ID_GATT, defs.GATT_WRITE_LONG,
                   CONTROLLER_INDEX),
    "cfg_notify": (defs.BTP_SERVICE_ID_GATT, defs.GATT_CFG_NOTIFY,
                   CONTROLLER_INDEX),
    "cfg_indicate": (defs.BTP_SERVICE_ID_GATT, defs.GATT_CFG_INDICATE,
                     CONTROLLER_INDEX),
}

L2CAP = {
    "read_supp_cmds": (defs.BTP_SERVICE_ID_L2CAP,
                       defs.L2CAP_READ_SUPPORTED_COMMANDS,
                       defs.BTP_INDEX_NONE, ""),
    "connect": (defs.BTP_SERVICE_ID_L2CAP, defs.L2CAP_CONNECT,
                CONTROLLER_INDEX),
    "disconnect": (defs.BTP_SERVICE_ID_L2CAP, defs.L2CAP_DISCONNECT,
                   CONTROLLER_INDEX),
    "send_data": (defs.BTP_SERVICE_ID_L2CAP, defs.L2CAP_SEND_DATA,
                  CONTROLLER_INDEX),
    "listen": (defs.BTP_SERVICE_ID_L2CAP, defs.L2CAP_LISTEN,
               CONTROLLER_INDEX),
}

MESH = {
    "read_supp_cmds": (defs.BTP_SERVICE_ID_MESH,
                       defs.MESH_READ_SUPPORTED_COMMANDS,
                       defs.BTP_INDEX_NONE, ""),
    "config_prov": (defs.BTP_SERVICE_ID_MESH,
                    defs.MESH_CONFIG_PROVISIONING,
                    CONTROLLER_INDEX),
    "prov_node": (defs.BTP_SERVICE_ID_MESH,
                  defs.MESH_PROVISION_NODE,
                  CONTROLLER_INDEX),
    "init": (defs.BTP_SERVICE_ID_MESH,
             defs.MESH_INIT,
             CONTROLLER_INDEX, ""),
    "reset": (defs.BTP_SERVICE_ID_MESH,
              defs.MESH_RESET,
              CONTROLLER_INDEX, ""),
    "input_num": (defs.BTP_SERVICE_ID_MESH,
                  defs.MESH_INPUT_NUMBER,
                  CONTROLLER_INDEX),
    "input_str": (defs.BTP_SERVICE_ID_MESH,
                  defs.MESH_INPUT_STRING,
                  CONTROLLER_INDEX),
    "iv_update_test_mode": (defs.BTP_SERVICE_ID_MESH,
                            defs.MESH_IV_UPDATE_TEST_MODE,
                            CONTROLLER_INDEX),
    "iv_update_toggle": (defs.BTP_SERVICE_ID_MESH,
                         defs.MESH_IV_UPDATE_TOGGLE,
                         CONTROLLER_INDEX, ""),
    "net_send": (defs.BTP_SERVICE_ID_MESH,
                 defs.MESH_NET_SEND,
                 CONTROLLER_INDEX),
    "health_generate_faults": (defs.BTP_SERVICE_ID_MESH,
                               defs.MESH_HEALTH_ADD_FAULTS,
                               CONTROLLER_INDEX, ""),
    "mesh_clear_faults": (defs.BTP_SERVICE_ID_MESH,
                          defs.MESH_HEALTH_CLEAR_FAULTS,
                          CONTROLLER_INDEX, ""),
    "lpn": (defs.BTP_SERVICE_ID_MESH,
            defs.MESH_LPN_SET,
            CONTROLLER_INDEX),
    "lpn_poll": (defs.BTP_SERVICE_ID_MESH,
                 defs.MESH_LPN_POLL,
                 CONTROLLER_INDEX, ""),
    "model_send": (defs.BTP_SERVICE_ID_MESH,
                   defs.MESH_MODEL_SEND,
                   CONTROLLER_INDEX),
    "lpn_subscribe": (defs.BTP_SERVICE_ID_MESH,
                      defs.MESH_LPN_SUBSCRIBE,
                      CONTROLLER_INDEX),
    "lpn_unsubscribe": (defs.BTP_SERVICE_ID_MESH,
                        defs.MESH_LPN_UNSUBSCRIBE,
                        CONTROLLER_INDEX),
    "rpl_clear": (defs.BTP_SERVICE_ID_MESH,
                  defs.MESH_RPL_CLEAR,
                  CONTROLLER_INDEX, ""),
    "proxy_identity": (defs.BTP_SERVICE_ID_MESH,
                       defs.MESH_PROXY_IDENTITY,
                       CONTROLLER_INDEX, ""),
}


def btp_hdr_check(rcv_hdr, exp_svc_id, exp_op=None):
    if rcv_hdr.svc_id != exp_svc_id:
        raise BTPError("Incorrect service ID %s in the response, expected %s!"
                       % (rcv_hdr.svc_id, exp_svc_id))

    if rcv_hdr.op == defs.BTP_STATUS:
        raise BTPError("Error opcode in response!")

    if exp_op and exp_op != rcv_hdr.op:
        raise BTPError(
            "Invalid opcode 0x%.2x in the response, expected 0x%.2x!" %
            (rcv_hdr.op, exp_op))


def core_reg_svc_gap(iutctl: IutCtl):
    logging.debug("%s", core_reg_svc_gap.__name__)

    iutctl.btp_worker.send(*CORE['gap_reg'])

    core_reg_svc_rsp_succ(iutctl)


def core_unreg_svc_gap(iutctl: IutCtl):
    logging.debug("%s", core_unreg_svc_gap.__name__)

    iutctl.btp_worker.send(*CORE['gap_unreg'])

    core_unreg_svc_rsp_succ(iutctl)


def core_reg_svc_gatt(iutctl: IutCtl):
    logging.debug("%s", core_reg_svc_gatt.__name__)

    iutctl.btp_worker.send(*CORE['gatt_reg'])

    core_reg_svc_rsp_succ(iutctl)


def core_unreg_svc_gatt(iutctl: IutCtl):
    logging.debug("%s", core_unreg_svc_gatt.__name__)

    iutctl.btp_worker.send_wait_rsp(*CORE['gatt_unreg'])


def core_reg_svc_l2cap(iutctl: IutCtl):
    logging.debug("%s", core_reg_svc_l2cap.__name__)

    iutctl.btp_worker.send(*CORE['l2cap_reg'])

    core_reg_svc_rsp_succ(iutctl)


def core_unreg_svc_l2cap(iutctl: IutCtl):
    logging.debug("%s", core_unreg_svc_l2cap.__name__)

    iutctl.btp_worker.send_wait_rsp(*CORE['l2cap_unreg'])


def core_reg_svc_mesh(iutctl: IutCtl):
    logging.debug("%s", core_reg_svc_mesh.__name__)

    iutctl.btp_worker.send(*CORE['mesh_reg'])

    core_reg_svc_rsp_succ(iutctl)


def core_unreg_svc_mesh(iutctl: IutCtl):
    logging.debug("%s", core_unreg_svc_mesh.__name__)

    iutctl.btp_worker.send_wait_rsp(*CORE['mesh_unreg'])


def core_reg_svc_rsp_succ(iutctl: IutCtl):
    logging.debug("%s", core_reg_svc_rsp_succ.__name__)

    expected_frame = ((defs.BTP_SERVICE_ID_CORE,
                       defs.CORE_REGISTER_SERVICE,
                       defs.BTP_INDEX_NONE,
                       0),
                      (b'',))

    tuple_hdr, tuple_data = iutctl.btp_worker.read()

    logging.debug("received %r %r", tuple_hdr, tuple_data)
    logging.debug("expected %r", expected_frame)

    if (tuple_hdr, tuple_data) != expected_frame:
        logging.error("frames mismatch")
        raise BTPError("Unexpected response received!")
    else:
        logging.debug("response is valid")


def core_unreg_svc_rsp_succ(iutctl: IutCtl):
    logging.debug("%s", core_unreg_svc_rsp_succ.__name__)

    expected_frame = ((defs.BTP_SERVICE_ID_CORE,
                       defs.CORE_UNREGISTER_SERVICE,
                       defs.BTP_INDEX_NONE,
                       0),
                      ('',))

    tuple_hdr, tuple_data = iutctl.btp_worker.read()

    logging.debug("received %r %r", tuple_hdr, tuple_data)
    logging.debug("expected %r", expected_frame)

    if (tuple_hdr, tuple_data) != expected_frame:
        logging.error("frames mismatch")
        raise BTPError("Unexpected response received!")
    else:
        logging.debug("response is valid")


def __gap_current_settings_update(gap, settings):
    logging.debug("%s %r", __gap_current_settings_update.__name__, settings)
    if isinstance(settings, tuple):
        fmt = '<I'
        if len(settings[0]) != struct.calcsize(fmt):
            raise BTPError("Invalid data length")

        settings = struct.unpack(fmt, settings[0])
        settings = settings[0]  # Result of unpack is always a tuple
        logging.debug("%s %r", __gap_current_settings_update.__name__, settings)

    for bit in gap_settings_btp2txt:
        if settings & (1 << bit):
            gap.current_settings_set(gap_settings_btp2txt[bit])
        else:
            gap.current_settings_clear(gap_settings_btp2txt[bit])


def gap_wait_for_connection(iutctl: IutCtl, timeout=10,
                            addr: BleAddress = None):
    logging.debug("%s %r", gap_wait_for_connection.__name__, addr)
    iutctl.stack.gap.wait_for_connection(timeout, addr)


def gap_wait_for_disconnection(iutctl: IutCtl, timeout=10,
                               addr: BleAddress = None):
    logging.debug("%s %r", gap_wait_for_disconnection.__name__, addr)
    iutctl.stack.gap.wait_for_disconnection(timeout, addr)


def parse_ad(ad):
    pos = 0
    total_len = len(ad)
    records = []

    while pos < total_len:
        length = ad[pos]
        pos += 1
        data = ad[pos:pos + length]
        assert len(data) == length
        ad_data_type = data[0]
        ad_data = data[1:length]
        records.append((ad_data_type, ad_data))
        pos += length

    return records


def ad_find_name(ad):
    name = ''
    short = ''
    for type, data in ad:
        if type == AdType.name_full:
            name = data.decode()
        elif type == AdType.name_short:
            short = data.decode()

    return name, short


def ad_find_uuid16(ad):
    bytes = 2
    uuids = []
    for type, data in ad:
        if type in [AdType.uuid16_some, AdType.uuid16_full]:
            split = [data[i:i + bytes] for i in range(0, len(data), bytes)]
            for u in split:
                uuids.append(btp2uuid(len(u), u))

    return uuids


def gap_adv_ind_on(iutctl: IutCtl, ad=None, sd=None):
    logging.debug("%s %r %r", gap_adv_ind_on.__name__, ad, sd)

    if iutctl.stack.gap.current_settings_get(
            gap_settings_btp2txt[defs.GAP_SETTINGS_ADVERTISING]):
        return

    data_ba = bytearray()
    ad_ba = bytearray()
    sd_ba = bytearray()

    if ad:
        for entry in ad:
            if isinstance(entry[1], str):
                data = binascii.unhexlify(entry[1])[::-1]
            else:
                data = entry[1]
            ad_ba.extend([entry[0]])
            ad_ba.extend([len(data)])
            ad_ba.extend(data)

    if sd:
        for entry in sd:
            if isinstance(entry[1], str):
                data = binascii.unhexlify(entry[1])[::-1]
            else:
                data = entry[1]
            ad_ba.extend([entry[0]])
            ad_ba.extend([len(data)])
            sd_ba.extend(data)

    data_ba.extend([len(ad_ba)])
    data_ba.extend([len(sd_ba)])
    data_ba.extend(ad_ba)
    data_ba.extend(sd_ba)

    iutctl.btp_worker.send(*GAP['start_adv'], data=data_ba)

    tuple_data = gap_command_rsp_succ(iutctl, defs.GAP_START_ADVERTISING)
    __gap_current_settings_update(iutctl.stack.gap, tuple_data)


def gap_adv_off(iutctl: IutCtl):
    logging.debug("%s", gap_adv_off.__name__)

    if not iutctl.stack.gap.current_settings_get(
            gap_settings_btp2txt[defs.GAP_SETTINGS_ADVERTISING]):
        return

    iutctl.btp_worker.send(*GAP['stop_adv'])

    tuple_data = gap_command_rsp_succ(iutctl, defs.GAP_STOP_ADVERTISING)
    __gap_current_settings_update(iutctl.stack.gap, tuple_data)


def gap_conn(iutctl: IutCtl, bd_addr: BleAddress):
    logging.debug("%s %r", gap_conn.__name__, bd_addr)

    data_ba = bytearray(bd_addr)

    iutctl.btp_worker.send(*GAP['conn'], data=data_ba)

    gap_command_rsp_succ(iutctl)


def gap_disconn(iutctl: IutCtl, bd_addr: BleAddress):
    logging.debug("%s %r", gap_disconn.__name__, bd_addr)

    if not iutctl.stack.gap.is_connected():
        return

    data_ba = bytearray(bd_addr)

    iutctl.btp_worker.send(*GAP['disconn'], data=data_ba)

    gap_command_rsp_succ(iutctl)


def verify_not_connected(iutctl: IutCtl, description):
    logging.debug("%s", verify_not_connected.__name__)

    gap_wait_for_connection(iutctl, 5)

    if iutctl.stack.gap.is_connected():
        return False
    return True


def gap_set_io_cap(iutctl: IutCtl, io_cap):
    logging.debug("%s %r", gap_set_io_cap.__name__, io_cap)

    iutctl.btp_worker.send(*GAP['set_io_cap'], data=chr(io_cap))

    gap_command_rsp_succ(iutctl)


def gap_pair(iutctl: IutCtl, bd_addr: BleAddress):
    logging.debug("%s %r", gap_pair.__name__, bd_addr)

    data_ba = bytearray(bd_addr)

    iutctl.btp_worker.send(*GAP['pair'], data=data_ba)

    # Expected result
    gap_command_rsp_succ(iutctl)


def gap_unpair(iutctl: IutCtl, bd_addr: BleAddress):
    logging.debug("%s %r", gap_unpair.__name__, bd_addr)

    data_ba = bytearray(bd_addr)

    iutctl.btp_worker.send(*GAP['unpair'], data=data_ba)

    # Expected result
    gap_command_rsp_succ(iutctl, defs.GAP_UNPAIR)


def var_store_get_passkey(iutctl: IutCtl):
    return str(iutctl.stack.gap.get_passkey())


def var_store_get_wrong_passkey(iutctl: IutCtl):
    passkey = iutctl.stack.gap.get_passkey()

    # Passkey is in range 0-999999
    if passkey > 0:
        return str(passkey - 1)
    else:
        return str(passkey + 1)


def gap_passkey_entry_rsp(iutctl: IutCtl, bd_addr: BleAddress, passkey):
    logging.debug("%s %r", gap_passkey_entry_rsp.__name__, bd_addr)

    data_ba = bytearray(bd_addr)

    if isinstance(passkey, str):
        passkey = int(passkey, 32)

    passkey_ba = struct.pack('I', passkey)
    data_ba.extend(passkey_ba)

    iutctl.btp_worker.send(*GAP['passkey_entry_rsp'], data=data_ba)

    gap_command_rsp_succ(iutctl)


def gap_reset(iutctl: IutCtl):
    logging.debug("%s", gap_reset.__name__)

    iutctl.btp_worker.send(*GAP['reset'])

    gap_command_rsp_succ(iutctl)


def gap_passkey_entry_req_ev(iutctl: IutCtl, bd_addr: BleAddress):
    logging.debug("%s %r", gap_passkey_entry_req_ev.__name__, bd_addr)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GAP,
                  defs.GAP_EV_PASSKEY_ENTRY_REQ)

    fmt = '<B6s'
    if len(tuple_data[0]) != struct.calcsize(fmt):
        raise BTPError("Invalid data length")

    # Unpack and swap address
    _addr_type, _addr = struct.unpack(fmt, tuple_data[0])
    _addr = binascii.hexlify(_addr[::-1]).lower().decode()

    if _addr_type != bd_addr.addr_type or _addr != bd_addr.addr:
        raise BTPError("Received data mismatch")


def gap_passkey_confirm(iutctl: IutCtl, bd_addr: BleAddress, match):
    logging.debug("%s %r", gap_passkey_confirm.__name__, bd_addr)

    data_ba = bytearray(bd_addr)
    data_ba.extend([match])

    iutctl.btp_worker.send(*GAP['passkey_confirm'], data=data_ba)

    gap_command_rsp_succ(iutctl)


def gap_set_conn(iutctl: IutCtl):
    logging.debug("%s", gap_set_conn.__name__)

    if iutctl.stack.gap.current_settings_get(
            gap_settings_btp2txt[defs.GAP_SETTINGS_CONNECTABLE]):
        return

    iutctl.btp_worker.send(*GAP['set_conn'])

    tuple_data = gap_command_rsp_succ(iutctl)
    __gap_current_settings_update(iutctl.stack.gap, tuple_data)


def gap_set_nonconn(iutctl: IutCtl):
    logging.debug("%s", gap_set_nonconn.__name__)

    if not iutctl.stack.gap.current_settings_get(
            gap_settings_btp2txt[defs.GAP_SETTINGS_CONNECTABLE]):
        return

    iutctl.btp_worker.send(*GAP['set_nonconn'])

    tuple_data = gap_command_rsp_succ(iutctl)
    __gap_current_settings_update(iutctl.stack.gap, tuple_data)


def gap_set_nondiscov(iutctl: IutCtl):
    logging.debug("%s", gap_set_nondiscov.__name__)

    if not iutctl.stack.gap.current_settings_get(
            gap_settings_btp2txt[defs.GAP_SETTINGS_DISCOVERABLE]):
        return

    iutctl.btp_worker.send(*GAP['set_nondiscov'])

    tuple_data = gap_command_rsp_succ(iutctl)
    __gap_current_settings_update(iutctl.stack.gap, tuple_data)


def gap_set_gendiscov(iutctl: IutCtl):
    logging.debug("%s", gap_set_gendiscov.__name__)

    iutctl.btp_worker.send(*GAP['set_gendiscov'])

    tuple_data = gap_command_rsp_succ(iutctl)
    __gap_current_settings_update(iutctl.stack.gap, tuple_data)


def gap_set_limdiscov(iutctl: IutCtl):
    logging.debug("%s", gap_set_limdiscov.__name__)

    iutctl.btp_worker.send(*GAP['set_limdiscov'])

    tuple_data = gap_command_rsp_succ(iutctl)
    __gap_current_settings_update(iutctl.stack.gap, tuple_data)


def gap_set_powered_on(iutctl: IutCtl):
    logging.debug("%s", gap_set_powered_on.__name__)

    iutctl.btp_worker.send(*GAP['set_powered_on'])

    tuple_data = gap_command_rsp_succ(iutctl)
    __gap_current_settings_update(iutctl.stack.gap, tuple_data)


def gap_set_powered_off(iutctl: IutCtl):
    logging.debug("%s", gap_set_powered_off.__name__)

    iutctl.btp_worker.send(*GAP['set_powered_off'])

    tuple_data = gap_command_rsp_succ(iutctl)
    __gap_current_settings_update(iutctl.stack.gap, tuple_data)


def gap_start_discov(iutctl: IutCtl, transport='le', type='active',
                     mode='general'):
    """GAP Start Discovery function.

    Possible options (key: <values>):

    transport: <le, bredr>
    type: <active, passive>
    mode: <general, limited, observe>

    """
    logging.debug("%s", gap_start_discov.__name__)

    flags = 0

    if transport == "le":
        flags |= defs.GAP_DISCOVERY_FLAG_LE
    else:
        flags |= defs.GAP_DISCOVERY_FLAG_BREDR

    if type == "active":
        flags |= defs.GAP_DISCOVERY_FLAG_LE_ACTIVE_SCAN

    if mode == "limited":
        flags |= defs.GAP_DISCOVERY_FLAG_LIMITED
    elif mode == "observe":
        flags |= defs.GAP_DISCOVERY_FLAG_LE_OBSERVE

    iutctl.stack.gap.reset_discovery()

    iutctl.btp_worker.send(*GAP['start_discov'], data=chr(flags))

    gap_command_rsp_succ(iutctl)


def check_discov_results(iutctl: IutCtl, addr: BleAddress,
                         discovered=True, eir=None):
    logging.debug("%s %r %r %r", check_discov_results.__name__,
                  addr, discovered, eir)

    found = False

    devices = iutctl.stack.gap.found_devices.data

    for device in devices:
        logging.debug("matching %r", device)
        if addr != device.addr:
            continue
        if eir and eir != device.eir:
            continue

        found = True
        break

    if discovered == found:
        return True

    return False


def check_discov_results_by_name(iutctl: IutCtl, name_long, name_short):
    logging.debug("%s %r %r", check_discov_results_by_name.__name__,
                  name_long, name_short)

    devices = iutctl.stack.gap.found_devices.data

    for device in devices:
        logging.debug("matching %r", device)
        ad = parse_ad(device.eir)
        long, short = ad_find_name(ad)
        if name_long == long and name_short == short:
            return device

    return None


def check_discov_results_by_uuid(iutctl: IutCtl, uuid):
    logging.debug("%s %r", check_discov_results_by_uuid.__name__, uuid)

    devices = iutctl.stack.gap.found_devices.data

    for device in devices:
        logging.debug("matching %r", device)
        ad = parse_ad(device.eir)
        uuids = ad_find_uuid16(ad)

        if uuid in uuids:
            return device

    return None


def gap_stop_discov(iutctl: IutCtl):
    logging.debug("%s", gap_stop_discov.__name__)

    iutctl.btp_worker.send(*GAP['stop_discov'])

    gap_command_rsp_succ(iutctl)

    iutctl.stack.gap.discoverying.data = False


def gap_conn_param_update(iutctl: IutCtl, addr: BleAddress, conn_itvl_min,
                          conn_itvl_max, conn_latency, supervision_timeout):
    logging.debug("%s %r %r %r %r %r", gap_conn_param_update.__name__, addr,
                  conn_itvl_min, conn_itvl_max,
                  conn_latency, supervision_timeout)

    data_ba = bytearray(addr)

    conn_itvl_min_ba = struct.pack('H', conn_itvl_min)
    conn_itvl_max_ba = struct.pack('H', conn_itvl_max)
    conn_latency_ba = struct.pack('H', conn_latency)
    supervision_timeout_ba = struct.pack('H', supervision_timeout)

    data_ba.extend(conn_itvl_min_ba)
    data_ba.extend(conn_itvl_max_ba)
    data_ba.extend(conn_latency_ba)
    data_ba.extend(supervision_timeout_ba)

    iutctl.btp_worker.send(*GAP['conn_param_update'], data=data_ba)

    gap_command_rsp_succ(iutctl, defs.GAP_CONN_PARAM_UPDATE)


def gap_read_ctrl_info(iutctl: IutCtl):
    logging.debug("%s", gap_read_ctrl_info.__name__)

    iutctl.btp_worker.send(*GAP['read_ctrl_info'])

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GAP,
                  defs.GAP_READ_CONTROLLER_INFO)

    fmt = '<6sII3s249s11s'
    if len(tuple_data[0]) < struct.calcsize(fmt):
        raise BTPError("Invalid data length")

    _addr, _supp_set, _curr_set, _cod, _name, _name_sh = \
        struct.unpack_from(fmt, tuple_data[0])
    _addr = binascii.hexlify(_addr[::-1]).lower().decode()

    addr_type = Addr.le_random if \
        (_curr_set & (1 << defs.GAP_SETTINGS_PRIVACY)) or \
        (_curr_set & (1 << defs.GAP_SETTINGS_STATIC_ADDRESS)) else \
        Addr.le_public

    name = _name.decode().rstrip('\0')
    name_short = _name_sh.decode().rstrip('\0')

    iutctl.stack.gap.name = name
    iutctl.stack.gap.name_short = name_short
    iutctl.stack.gap.iut_addr_set(BleAddress(_addr, addr_type))
    logging.debug("IUT address %r", iutctl.stack.gap.iut_addr_get())
    logging.debug("IUT name '%s' name short '%s'", name, name_short)

    __gap_current_settings_update(iutctl.stack.gap, _curr_set)


def gap_command_rsp_succ(iutctl: IutCtl, op=None):
    logging.debug("%s", gap_command_rsp_succ.__name__)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GAP, op)

    return tuple_data


def gap_identity_resolved_ev(iutctl: IutCtl):
    logging.debug("%s", gap_identity_resolved_ev.__name__)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GAP,
                  defs.GAP_EV_IDENTITY_RESOLVED)

    fmt = '<B6sB6s'
    if len(tuple_data[0]) != struct.calcsize(fmt):
        raise BTPError("Invalid data length")

    _addr_t, _addr, _id_addr_t, _id_addr = struct.unpack_from('<B6sB6s',
                                                              tuple_data[0])
    # Convert addresses to lower case
    _addr = binascii.hexlify(_addr[::-1]).lower().decode()
    _id_addr = binascii.hexlify(_id_addr[::-1]).lower().decode()


def gap_new_settings_ev_(gap, data, data_len):
    logging.debug("%s %r", gap_new_settings_ev_.__name__, data)

    data_fmt = '<I'

    curr_set, = struct.unpack_from(data_fmt, data)

    __gap_current_settings_update(gap, curr_set)


def gap_device_found_ev_(gap, data, data_len):
    logging.debug("%s %r", gap_device_found_ev_.__name__, data)

    fmt = '<B6sBBH'
    if len(data) < struct.calcsize(fmt):
        raise BTPError("Invalid data length")

    addr_type, addr, rssi, flags, eir_len = struct.unpack_from(fmt, data)
    eir = data[struct.calcsize(fmt):]

    if len(eir) != eir_len:
        raise BTPError("Invalid data length")

    addr = binascii.hexlify(addr[::-1]).lower().decode()

    logging.debug("found %r type %r eir %r", addr, addr_type, eir)

    gap.found_devices.data.append(LeAdv(BleAddress(addr, addr_type), rssi,
                                        flags, eir))


def gap_connected_ev_(gap, data, data_len):
    logging.debug("%s %r", gap_connected_ev_.__name__, data)

    hdr_fmt = '<B6sHHH'
    hdr_len = struct.calcsize(hdr_fmt)

    addr_type, addr, itvl, latency, timeout = struct.unpack_from(hdr_fmt, data)
    addr = binascii.hexlify(addr[::-1]).decode()

    logging.debug("connected to %r type %r", addr, addr_type)

    gap.connected(BleAddress(addr, addr_type))
    gap.set_conn_params(ConnParams(itvl, latency, timeout))


def gap_disconnected_ev_(gap, data, data_len):
    logging.debug("%s %r", gap_disconnected_ev_.__name__, data)

    hdr_fmt = '<B6s'
    hdr_len = struct.calcsize(hdr_fmt)

    addr_type, addr = struct.unpack_from(hdr_fmt, data)
    addr = binascii.hexlify(addr[::-1]).decode()

    logging.debug("disconnected from %r type %r", addr, addr_type)

    gap.disconnected(BleAddress(addr, addr_type))


def gap_passkey_disp_ev_(gap, data, data_len):
    logging.debug("%s %r", gap_passkey_disp_ev_.__name__, data)

    fmt = '<B6sI'

    addr_type, addr, passkey = struct.unpack(fmt, data)
    addr = binascii.hexlify(addr[::-1])

    logging.debug("passkey = %r", passkey)

    gap.passkey.data = passkey


def gap_passkey_confirm_req_ev_(gap, data, data_len):
    logging.debug("%s %r", gap_passkey_disp_ev_.__name__, data)

    fmt = '<B6sI'

    addr_type, addr, passkey = struct.unpack(fmt, data)
    addr = binascii.hexlify(addr[::-1])

    logging.debug("passkey = %r", passkey)

    gap.passkey.data = passkey


def gap_conn_param_udpate_ev(iutctl: IutCtl):
    logging.debug("%s", gap_conn_param_udpate_ev.__name__)

    tuple_hdr, data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GAP,
                  defs.GAP_EV_CONN_PARAM_UPDATE)

    fmt = '<B6sHHH'
    if len(data[0]) != struct.calcsize(fmt):
        raise BTPError("Invalid data length")

    # Unpack and swap address
    _addr_t, _addr, _itvl, _latency, _timeout = struct.unpack_from(fmt, data[0])
    _addr = binascii.hexlify(_addr[::-1]).lower()

    iutctl.stack.gap.set_conn_params(ConnParams(_itvl, _latency, _timeout))


def gap_conn_param_update_ev_(gap, data, data_len):
    logging.debug("%s", gap_conn_param_update_ev_.__name__)

    logging.debug("received %r", data)

    fmt = '<B6sHHH'
    if len(data) != struct.calcsize(fmt):
        raise BTPError("Invalid data length")

    _addr_t, _addr, _itvl, _latency, _timeout = struct.unpack_from(fmt, data)
    _addr = binascii.hexlify(_addr[::-1]).lower()

    logging.debug("received %r", (_addr_t, _addr, _itvl, _latency, _timeout))

    gap.set_conn_params(ConnParams(_itvl, _latency, _timeout))


GAP_EV = {
    defs.GAP_EV_NEW_SETTINGS: gap_new_settings_ev_,
    defs.GAP_EV_DEVICE_FOUND: gap_device_found_ev_,
    defs.GAP_EV_DEVICE_CONNECTED: gap_connected_ev_,
    defs.GAP_EV_DEVICE_DISCONNECTED: gap_disconnected_ev_,
    defs.GAP_EV_PASSKEY_DISPLAY: gap_passkey_disp_ev_,
    defs.GAP_EV_PASSKEY_CONFIRM_REQ: gap_passkey_confirm_req_ev_,
    defs.GAP_EV_CONN_PARAM_UPDATE: gap_conn_param_update_ev_,
}


def gatts_add_svc(iutctl: IutCtl, svc_type, uuid):
    logging.debug("%s %r %r", gatts_add_svc.__name__, svc_type, uuid)

    data_ba = bytearray()
    uuid_ba = binascii.unhexlify(uuid.replace("-", ""))[::-1]

    data_ba.extend([svc_type])
    data_ba.extend([len(uuid_ba)])
    data_ba.extend(uuid_ba)

    iutctl.btp_worker.send(*GATTS['add_svc'], data=data_ba)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_ADD_SERVICE)

    data = struct.unpack('H', tuple_data[0])
    return data[0]


def gatts_add_inc_svc(iutctl: IutCtl, hdl):
    logging.debug("%s %r", gatts_add_inc_svc.__name__, hdl)

    if type(hdl) is str:
        hdl = int(hdl, 16)

    data_ba = bytearray()
    hdl_ba = struct.pack('H', hdl)
    data_ba.extend(hdl_ba)

    iutctl.btp_worker.send(*GATTS['add_inc_svc'], data=data_ba)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_ADD_INCLUDED_SERVICE)

    data = struct.unpack('H', tuple_data[0])
    return data[0]


def gatts_add_char(iutctl: IutCtl, hdl, prop, perm, uuid):
    logging.debug("%s %r %r %r %r", gatts_add_char.__name__, hdl, prop, perm,
                  uuid)

    if type(hdl) is str:
        hdl = int(hdl, 16)

    data_ba = bytearray()
    hdl_ba = struct.pack('H', hdl)
    uuid_ba = binascii.unhexlify(uuid.replace("-", ""))[::-1]

    data_ba.extend(hdl_ba)
    data_ba.extend([prop])
    data_ba.extend([perm])
    data_ba.extend([len(uuid_ba)])
    data_ba.extend(uuid_ba)

    iutctl.btp_worker.send(*GATTS['add_char'], data=data_ba)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_ADD_CHARACTERISTIC)

    data = struct.unpack('H', tuple_data[0])
    return data[0]


def gatts_set_val(iutctl: IutCtl, hdl, val):
    logging.debug("%s %r %r ", gatts_set_val.__name__, hdl, val)

    if type(hdl) is str:
        hdl = int(hdl, 16)

    data_ba = bytearray()
    hdl_ba = struct.pack('H', hdl)
    val_ba = binascii.unhexlify(bytearray(val.encode()))
    val_len_ba = struct.pack('H', len(val_ba))

    data_ba.extend(hdl_ba)
    data_ba.extend(val_len_ba)
    data_ba.extend(val_ba)

    iutctl.btp_worker.send(*GATTS['set_val'], data=data_ba)

    gatt_command_rsp_succ(iutctl)


def gatts_add_desc(iutctl: IutCtl, hdl, perm, uuid):
    logging.debug("%s %r %r %r", gatts_add_desc.__name__, hdl, perm, uuid)

    if type(hdl) is str:
        hdl = int(hdl, 16)

    data_ba = bytearray()
    hdl_ba = struct.pack('H', hdl)
    uuid_ba = binascii.unhexlify(uuid.replace("-", ""))[::-1]

    data_ba.extend(hdl_ba)
    data_ba.extend([perm])
    data_ba.extend([len(uuid_ba)])
    data_ba.extend(uuid_ba)

    iutctl.btp_worker.send(*GATTS['add_desc'], data=data_ba)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_ADD_DESCRIPTOR)

    data = struct.unpack('H', tuple_data[0])
    return data[0]


def gatts_start_server(iutctl: IutCtl):
    logging.debug("%s", gatts_start_server.__name__)

    iutctl.btp_worker.send(*GATTS['start_server'])

    gatt_command_rsp_succ(iutctl)


def gatts_set_enc_key_size(iutctl: IutCtl, hdl, enc_key_size):
    logging.debug("%s %r %r", gatts_set_enc_key_size.__name__,
                  hdl, enc_key_size)

    if type(hdl) is str:
        hdl = int(hdl, 16)

    data_ba = bytearray()
    hdl_ba = struct.pack('H', hdl)

    data_ba.extend(hdl_ba)
    data_ba.extend([enc_key_size])

    iutctl.btp_worker.send(*GATTS['set_enc_key_size'], data=data_ba)

    gatt_command_rsp_succ(iutctl)


def gatts_dec_attr_value_changed_ev_data(frame):
    """Decodes BTP Attribute Value Changed Event data

    Event data frame format
    0             16            32
    +--------------+-------------+------+
    | Attribute ID | Data Length | Data |
    +--------------+-------------+------+

    """
    hdr = '<HH'
    hdr_len = struct.calcsize(hdr)

    (handle, data_len) = struct.unpack_from(hdr, frame)
    data = struct.unpack_from('%ds' % data_len, frame, hdr_len)

    return handle, data


def gatts_attr_value_changed_ev(iutctl: IutCtl):
    logging.debug("%s", gatts_attr_value_changed_ev.__name__)

    (tuple_hdr, tuple_data) = iutctl.btp_worker.read()

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_EV_ATTR_VALUE_CHANGED)

    (handle, data) = gatts_dec_attr_value_changed_ev_data(tuple_data[0])
    logging.debug("%s %r %r", gatts_attr_value_changed_ev.__name__,
                  handle, data)

    return handle, data


def gatts_verify_write_success(iutctl: IutCtl, description):
    """
    This verifies if PTS initiated write operation succeeded
    """
    logging.debug("%s", gatts_verify_write_success.__name__)

    # If write is successful, Attribute Value Changed Event will be received
    try:
        (handle, value) = gatts_attr_value_changed_ev(iutctl)
        logging.debug("%s Handle %r. Value %r has been successfully written",
                      gatts_verify_write_success.__name__, handle, value)
        return True
    except BaseException:
        logging.debug("%s PTS failed to write attribute value",
                      gatts_verify_write_success.__name__)
        return False


def gatts_verify_write_fail(iutctl: IutCtl, description):
    return not gatts_verify_write_success(iutctl, description)


def btp2uuid(uuid_len, uu):
    if uuid_len == 2:
        (uu,) = struct.unpack("H", uu)
        return format(uu, 'x').upper()
    else:
        return uuid.UUID(bytes=uu[::-1]).urn[9:].replace('-', '').upper()


def gatt_server_fetch_db(iutctl: IutCtl, db: GattDB, start_handle=0x0001,
                         end_handle=0xffff, type_uuid=None):
    char_val_set = set()

    attrs = gatts_get_attrs(iutctl, start_handle, end_handle, type_uuid)
    for attr in attrs:
        handle, perm, type_uuid = attr

        attr_val = gatts_get_attr_val(iutctl, handle)
        if not attr_val:
            logging.debug("cannot read value %r", handle)
            continue

        att_rsp, val_len, val = attr_val

        if handle in char_val_set:
            char_val_set.remove(handle)
            continue

        if type_uuid == '2800' or type_uuid == '2801':
            uuid = btp2uuid(val_len, val)

            if type_uuid == '2800':
                db.attr_add(handle,
                            GattPrimary(handle, perm, uuid, att_rsp, None))
            else:
                db.attr_add(handle,
                            GattSecondary(handle, perm, uuid, att_rsp, None))
        elif type_uuid == '2803':

            hdr = '<BH'
            hdr_len = struct.calcsize(hdr)
            uuid_len = val_len - hdr_len

            prop, value_handle, uuid = struct.unpack("<BH%ds" % uuid_len, val)
            uuid = btp2uuid(uuid_len, uuid)

            char_val_set.add(value_handle)

            db.attr_add(handle,
                        GattCharacteristic(handle, perm, uuid, att_rsp, prop,
                                           value_handle))
        elif type_uuid == '2802':
            hdr = "<HH"
            hdr_len = struct.calcsize(hdr)
            uuid_len = val_len - hdr_len
            incl_svc_hdl, end_grp_hdl, uuid = struct.unpack(
                hdr + "%ds" % uuid_len, val)
            if uuid_len > 0:
                uuid = btp2uuid(uuid_len, uuid)
            else:
                uuid = None

            db.attr_add(handle, GattServiceIncluded(handle, perm, uuid, att_rsp,
                                                    incl_svc_hdl, end_grp_hdl))
        else:
            uuid = type_uuid.replace("0x", "").replace("-", "").upper()

            db.attr_add(handle, GattCharacteristicDescriptor(handle, perm, uuid,
                                                             att_rsp, val))


def dec_gatts_get_attrs_rp(data, data_len):
    logging.debug("%s %r %r", dec_gatts_get_attrs_rp.__name__, data, data_len)

    hdr = '<B'
    hdr_len = struct.calcsize(hdr)
    data_len = data_len - hdr_len

    (attr_count, attrs) = struct.unpack(hdr + '%ds' % data_len, data)

    attributes = []

    while (attr_count - 1) >= 0:
        hdr = '<HBB'
        hdr_len = struct.calcsize(hdr)
        data_len = data_len - hdr_len

        (handle, permission, type_uuid_len, frag) = \
            struct.unpack(hdr + '%ds' % data_len, attrs)

        data_len = data_len - type_uuid_len

        (type_uuid, attrs) = struct.unpack('%ds%ds' % (type_uuid_len,
                                                       data_len), frag)

        type_uuid = btp2uuid(type_uuid_len, type_uuid)

        attributes.append((handle, permission, type_uuid))

        attr_count = attr_count - 1

        logging.debug("handle %r perm %r type_uuid %r", handle, permission,
                      type_uuid)

    return attributes


def gatts_get_attrs(iutctl: IutCtl, start_handle=0x0001,
                    end_handle=0xffff, type_uuid=None):
    logging.debug("%s %r %r %r", gatts_get_attrs.__name__, start_handle,
                  end_handle, type_uuid)

    data_ba = bytearray()

    if type(start_handle) is str:
        start_handle = int(start_handle, 16)

    start_hdl_ba = struct.pack('H', start_handle)
    data_ba.extend(start_hdl_ba)

    if type(end_handle) is str:
        end_handle = int(end_handle, 16)

    end_hdl_ba = struct.pack('H', end_handle)
    data_ba.extend(end_hdl_ba)

    if type_uuid:
        uuid_ba = binascii.unhexlify(type_uuid.replace("-", ""))[::-1]
        data_ba.extend([len(uuid_ba)])
        data_ba.extend(uuid_ba)
    else:
        data_ba.extend([0])

    iutctl.btp_worker.send(*GATTS['get_attrs'], data=data_ba)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_GET_ATTRIBUTES)

    return dec_gatts_get_attrs_rp(tuple_data[0], tuple_hdr.data_len)


def gatts_get_attr_val(iutctl: IutCtl, handle):
    logging.debug("%s %r", gatts_get_attr_val.__name__, handle)

    data_ba = bytearray()

    if type(handle) is str:
        handle = int(handle, 16)

    hdl_ba = struct.pack('H', handle)
    data_ba.extend(hdl_ba)

    iutctl.btp_worker.send(*GATTS['get_attr_val'], data=data_ba)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_GET_ATTRIBUTE_VALUE)

    hdr = '<BH'
    hdr_len = struct.calcsize(hdr)
    data_len = tuple_hdr.data_len - hdr_len

    return struct.unpack(hdr + '%ds' % data_len, tuple_data[0])


def gatts_parse_attribute(hdl, perm, type_uuid, data):
    att_rsp, val_len, value = data

    if (type_uuid == UUID.primary_svc) or \
            (type_uuid == UUID.secondary_svc):
        svc_uuid = btp2uuid(len(value), value)
        return ("service", (hdl, 0xffff, svc_uuid))
    elif type_uuid == UUID.include_svc:
        hdr = '<HH'
        hdr_len = struct.calcsize(hdr)

        incl_hdl, end_hdl = struct.unpack_from(hdr, value)
        incl_uuid = None

        uuid_len = len(value) - hdr_len
        if uuid_len > 0:
            uuid = struct.unpack_from('%ds' % uuid_len, value[hdr_len:])
            incl_uuid = btp2uuid(uuid_len, uuid[0])

        return ("include", (hdl, incl_hdl, end_hdl, incl_uuid))
    elif type_uuid == UUID.chrc:
        hdr = '<BH'
        hdr_len = struct.calcsize(hdr)

        props, val_hdl = struct.unpack_from(hdr, value)

        uuid_len = len(value) - hdr_len
        uuid = struct.unpack_from('%ds' % uuid_len, value[hdr_len:])
        chr_uuid = btp2uuid(uuid_len, uuid[0])

        return ("characteristic", (hdl, val_hdl, props, chr_uuid))
    else:
        return ("descriptor", (hdl, type_uuid))


def gatts_get_attribute_values(iutctl: IutCtl, attributes):
    database = {}
    store_chr_def = None

    for attr in attributes:
        hdl, perm, type_uuid = attr
        rsp = gatts_get_attr_val(iutctl, hdl)

        if store_chr_def:
            _, _, _, chr_uuid = store_chr_def[1]
            store_chr_def = None
            if type_uuid == chr_uuid:
                continue

        attribute = gatts_parse_attribute(hdl, perm, type_uuid, rsp)

        if attribute[0] == 'characteristic':
            store_chr_def = attribute

        database[hdl] = attribute

    return database


def gattc_exchange_mtu(iutctl: IutCtl, bd_addr: BleAddress):
    logging.debug("%s %r", gattc_exchange_mtu.__name__, bd_addr)

    gap_wait_for_connection(iutctl)

    data_ba = bytearray(bd_addr)

    iutctl.btp_worker.send(*GATTC['exchange_mtu'], data=data_ba)

    gatt_command_rsp_succ(iutctl)


def gattc_disc_prim_svcs(iutctl: IutCtl, bd_addr: BleAddress):
    logging.debug("%s %r", gattc_disc_prim_svcs.__name__, bd_addr)

    gap_wait_for_connection(iutctl)

    data_ba = bytearray(bd_addr)

    iutctl.btp_worker.send(*GATTC['disc_prim_svcs'], data=data_ba)


def gattc_disc_prim_uuid(iutctl: IutCtl, bd_addr: BleAddress, uuid):
    logging.debug("%s %r %r", gattc_disc_prim_uuid.__name__, bd_addr, uuid)

    gap_wait_for_connection(iutctl)

    data_ba = bytearray(bd_addr)

    uuid_ba = binascii.unhexlify(uuid.replace('-', ''))[::-1]

    data_ba.extend([len(uuid_ba)])
    data_ba.extend(uuid_ba)

    iutctl.btp_worker.send(*GATTC['disc_prim_uuid'], data=data_ba)


def gattc_find_included(iutctl: IutCtl, bd_addr: BleAddress,
                        start_hdl, stop_hdl):
    logging.debug("%s %r %r %r", gattc_find_included.__name__,
                  bd_addr, start_hdl, stop_hdl)

    gap_wait_for_connection(iutctl)

    if type(stop_hdl) is str:
        stop_hdl = int(stop_hdl, 16)

    if type(start_hdl) is str:
        start_hdl = int(start_hdl, 16)

    data_ba = bytearray(bd_addr)

    start_hdl_ba = struct.pack('H', start_hdl)
    stop_hdl_ba = struct.pack('H', stop_hdl)

    data_ba.extend(start_hdl_ba)
    data_ba.extend(stop_hdl_ba)

    iutctl.btp_worker.send(*GATTC['find_included'], data=data_ba)


def gattc_disc_all_chrc_find_attrs_rsp(iutctl: IutCtl, exp_chars,
                                       store_attrs=False):
    """Parse and find requested characteristics from rsp

    ATTRIBUTE FORMAT (CHARACTERISTIC) - (handle, val handle, props, uuid)

    """
    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r",
                  gattc_disc_all_chrc_find_attrs_rsp.__name__, tuple_hdr,
                  tuple_data)
    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_DISC_ALL_CHRC)

    chars_tuple = gatt_dec_disc_rsp(tuple_data[0], "characteristic")

    for char in chars_tuple:
        for exp_char in exp_chars:
            # Check if option expected attribute parameters match
            char_uuid = binascii.hexlify(char[3][0][::-1])
            if ((exp_char[0] and exp_char[0] != char[0]) or
                    (exp_char[1] and exp_char[1] != char[1]) or
                    (exp_char[2] and exp_char[2] != char[2]) or
                    (exp_char[3] and exp_char[3] != char_uuid)):
                logging.debug("gatt char not matched = %r != %r", char,
                              exp_char)

                continue

            logging.debug("gatt char matched = %r == %r", char, exp_char)


def gattc_disc_all_chrc(iutctl: IutCtl, bd_addr: BleAddress, start_hdl,
                        stop_hdl,
                        svc=None):
    logging.debug("%s %r %r %r %r", gattc_disc_all_chrc.__name__,
                  bd_addr, start_hdl, stop_hdl, svc)

    gap_wait_for_connection(iutctl)

    if svc:
        svc_nb = svc[1]
        # TODO:
        for s in iutctl.stack.gatt.svcs:
            if not ((svc[0][0] and svc[0][0] != s[0]) and
                    (svc[0][1] and svc[0][1] != s[1]) and
                    (svc[0][2] and svc[0][2] != s[2])):

                # To take n-th service
                svc_nb -= 1
                if svc_nb != 0:
                    continue

                start_hdl = s[0]
                stop_hdl = s[1]

                logging.debug("Got requested service!")

                break

    if type(start_hdl) is str:
        start_hdl = int(start_hdl, 16)

    if type(stop_hdl) is str:
        stop_hdl = int(stop_hdl, 16)

    data_ba = bytearray(bd_addr)

    start_hdl_ba = struct.pack('H', start_hdl)
    stop_hdl_ba = struct.pack('H', stop_hdl)

    data_ba.extend(start_hdl_ba)
    data_ba.extend(stop_hdl_ba)

    iutctl.btp_worker.send(*GATTC['disc_all_chrc'], data=data_ba)


def gattc_disc_chrc_uuid(iutctl: IutCtl, bd_addr: BleAddress,
                         start_hdl, stop_hdl, uuid):
    logging.debug("%s %r %r %r %r", gattc_disc_chrc_uuid.__name__,
                  bd_addr, start_hdl, stop_hdl, uuid)

    gap_wait_for_connection(iutctl)

    if type(stop_hdl) is str:
        stop_hdl = int(stop_hdl, 16)

    if type(start_hdl) is str:
        start_hdl = int(start_hdl, 16)

    data_ba = bytearray(bd_addr)

    start_hdl_ba = struct.pack('H', start_hdl)
    stop_hdl_ba = struct.pack('H', stop_hdl)

    if "-" in uuid:
        uuid = uuid.replace("-", "")
    if uuid.startswith("0x"):
        uuid = uuid.replace("0x", "")
    uuid_ba = binascii.unhexlify(uuid)[::-1]

    data_ba.extend(start_hdl_ba)
    data_ba.extend(stop_hdl_ba)
    data_ba.extend([len(uuid_ba)])
    data_ba.extend(uuid_ba)

    iutctl.btp_worker.send(*GATTC['disc_chrc_uuid'], data=data_ba)


def gattc_disc_all_desc(iutctl: IutCtl, bd_addr: BleAddress,
                        start_hdl, stop_hdl):
    logging.debug("%s %r %r %r", gattc_disc_all_desc.__name__,
                  bd_addr, start_hdl, stop_hdl)

    gap_wait_for_connection(iutctl)

    if type(start_hdl) is str:
        start_hdl = int(start_hdl, 16)

    if type(stop_hdl) is str:
        stop_hdl = int(stop_hdl, 16)

    data_ba = bytearray(bd_addr)

    start_hdl_ba = struct.pack('H', start_hdl)
    stop_hdl_ba = struct.pack('H', stop_hdl)

    data_ba.extend(start_hdl_ba)
    data_ba.extend(stop_hdl_ba)

    iutctl.btp_worker.send(*GATTC['disc_all_desc'], data=data_ba)


def gattc_disc_full(iutctl: IutCtl, bd_addr: BleAddress, db: GattDB):
    logging.debug("%s %r", gattc_disc_full.__name__, bd_addr)

    gap_wait_for_connection(iutctl)

    gattc_disc_prim_svcs(iutctl, bd_addr)
    gattc_disc_prim_svcs_rsp(iutctl, db)

    for svc in db.get_services():
        start, end = svc.handle, svc.end_hdl

        gattc_find_included(iutctl, bd_addr, start, end)
        gattc_find_included_rsp(iutctl, db)

        gattc_disc_all_chrc(iutctl, bd_addr, start, end)
        gattc_disc_all_chrc_rsp(iutctl, db)

    for char in db.get_characteristics():
        start_hdl = char.value_hdl + 1
        end_hdl = db.find_characteristic_end(char.handle)
        assert(end_hdl is not None)

        gattc_disc_all_desc(iutctl, bd_addr, start_hdl, end_hdl)
        gattc_disc_all_desc_rsp(iutctl, db)


def gattc_read_char_val(iutctl: IutCtl, bd_addr: BleAddress, char):
    logging.debug("%s %r %r", gattc_read_char_val.__name__,
                  bd_addr, char)

    char_nb = char[1]
    # TODO:
    for c in iutctl.stack.gatt.svcs:
        if not ((char[0][0] and char[0][0] != c[0]) and
                (char[0][1] and char[0][1] != c[1]) and
                (char[0][2] and char[0][2] != c[2])
                    (char[0][3] and char[0][3] != c[3])):

            # To take n-th service
            char_nb -= 1
            if char_nb != 0:
                continue

            logging.debug("Got requested char, val handle = %r!", c[1])

            gattc_read(iutctl, bd_addr, c[1])

            break


def gattc_read(iutctl: IutCtl, bd_addr: BleAddress, hdl):
    logging.debug("%s %r %r", gattc_read.__name__, bd_addr, hdl)

    gap_wait_for_connection(iutctl)

    data_ba = bytearray(bd_addr)

    if type(hdl) is str:
        hdl = int(hdl, 16)
    hdl_ba = struct.pack('H', hdl)

    data_ba.extend(hdl_ba)

    iutctl.btp_worker.send(*GATTC['read'], data=data_ba)


def gattc_read_long(iutctl: IutCtl, bd_addr: BleAddress,
                    hdl, off, modif_off=None):
    logging.debug("%s %r %r %r %r", gattc_read_long.__name__,
                  bd_addr, hdl, off, modif_off)

    gap_wait_for_connection(iutctl)

    data_ba = bytearray(bd_addr)

    if type(off) is str:
        off = int(off, 16)
    if modif_off:
        off += modif_off
    if type(hdl) is str:
        hdl = int(hdl, 16)

    hdl_ba = struct.pack('H', hdl)
    off_ba = struct.pack('H', off)

    data_ba.extend(hdl_ba)
    data_ba.extend(off_ba)

    iutctl.btp_worker.send(*GATTC['read_long'], data=data_ba)


def gattc_read_multiple(iutctl: IutCtl, bd_addr: BleAddress, *hdls):
    logging.debug("%s %r %r", gattc_read_multiple.__name__,
                  bd_addr, hdls)

    gap_wait_for_connection(iutctl)

    data_ba = bytearray(bd_addr)

    hdls_j = ''.join(hdl for hdl in hdls)
    hdls_byte_table = [hdls_j[i:i + 2] for i in range(0, len(hdls_j), 2)]
    hdls_swp = ''.join([c[1] + c[0] for c in zip(hdls_byte_table[::2],
                                                 hdls_byte_table[1::2])])
    hdls_ba = binascii.unhexlify(bytearray(hdls_swp))

    data_ba.extend([len(hdls)])
    data_ba.extend(hdls_ba)

    iutctl.btp_worker.send(*GATTC['read_multiple'], data=data_ba)


def gattc_write_without_rsp(iutctl: IutCtl, bd_addr: BleAddress, hdl, val,
                            val_mtp=None):
    logging.debug("%s %r %r %r %r", gattc_write_without_rsp.__name__,
                  bd_addr, hdl, val, val_mtp)

    gap_wait_for_connection(iutctl)

    if type(hdl) is str:
        hdl = int(hdl, 16)

    if val_mtp:
        val *= int(val_mtp)

    data_ba = bytearray()

    hdl_ba = struct.pack('H', hdl)
    val_ba = binascii.unhexlify(bytearray(val))
    val_len_ba = struct.pack('H', len(val_ba))

    data_ba.extend(hdl_ba)
    data_ba.extend(val_len_ba)
    data_ba.extend(val_ba)

    iutctl.btp_worker.send(*GATTC['write_without_rsp'], data=data_ba)

    gatt_command_rsp_succ(iutctl)


def gattc_signed_write(iutctl: IutCtl, bd_addr: BleAddress,
                       hdl, val, val_mtp=None):
    logging.debug("%s %r %r %r %r", gattc_signed_write.__name__,
                  bd_addr, hdl, val, val_mtp)

    gap_wait_for_connection(iutctl)

    if type(hdl) is str:
        hdl = int(hdl, 16)

    if val_mtp:
        val *= int(val_mtp)

    data_ba = bytearray(bd_addr)

    hdl_ba = struct.pack('H', hdl)
    val_ba = binascii.unhexlify(bytearray(val))
    val_len_ba = struct.pack('H', len(val_ba))

    data_ba.extend(hdl_ba)
    data_ba.extend(val_len_ba)
    data_ba.extend(val_ba)

    iutctl.btp_worker.send(*GATTC['signed_write'], data=data_ba)

    gatt_command_rsp_succ(iutctl)


def gattc_write(iutctl: IutCtl, bd_addr: BleAddress, hdl, val, val_mtp=None):
    logging.debug("%s %r %r %r %r", gattc_write.__name__,
                  bd_addr, hdl, val, val_mtp)

    gap_wait_for_connection(iutctl)

    if type(hdl) is str:
        hdl = int(hdl, 16)

    if val_mtp:
        val *= int(val_mtp)

    data_ba = bytearray(bd_addr)

    hdl_ba = struct.pack('H', hdl)
    val_ba = binascii.unhexlify(bytearray(val.encode()))
    val_len_ba = struct.pack('H', len(val_ba))

    data_ba.extend(hdl_ba)
    data_ba.extend(val_len_ba)
    data_ba.extend(val_ba)

    iutctl.btp_worker.send(*GATTC['write'], data=data_ba)


def gattc_write_long(iutctl: IutCtl, bd_addr: BleAddress, hdl, off, val,
                     length=None):
    logging.debug("%s %r %r %r %r", gattc_write_long.__name__,
                  hdl, off, val, length)

    gap_wait_for_connection(iutctl)

    if type(hdl) is str:
        hdl = int(hdl, 16)  # convert string in hex format to int

    if type(off) is str:
        off = int(off, 16)

    if length:
        val *= int(length)

    hdl_ba = struct.pack('H', hdl)
    off_ba = struct.pack('H', off)
    val_ba = binascii.unhexlify(bytearray(val.encode()))
    val_len_ba = struct.pack('H', len(val_ba))

    data_ba = bytearray(bd_addr)
    data_ba.extend(hdl_ba)
    data_ba.extend(off_ba)
    data_ba.extend(val_len_ba)
    data_ba.extend(val_ba)

    iutctl.btp_worker.send(*GATTC['write_long'], data=data_ba)


def gattc_cfg_notify(iutctl: IutCtl, bd_addr: BleAddress, enable, ccc_hdl):
    logging.debug("%s %r, %r, %r", gattc_cfg_notify.__name__,
                  bd_addr, enable, ccc_hdl)

    gap_wait_for_connection(iutctl)

    if type(ccc_hdl) is str:
        ccc_hdl = int(ccc_hdl, 16)

    ccc_hdl_ba = struct.pack('H', ccc_hdl)

    data_ba = bytearray(bd_addr)
    data_ba.extend([enable])
    data_ba.extend(ccc_hdl_ba)

    iutctl.btp_worker.send(*GATTC['cfg_notify'], data=data_ba)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_cfg_notify.__name__,
                  tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_CFG_NOTIFY)


def gattc_cfg_indicate(iutctl: IutCtl, bd_addr: BleAddress, enable, ccc_hdl):
    logging.debug("%s %r, %r, %r", gattc_cfg_indicate.__name__,
                  bd_addr, enable, ccc_hdl)

    if type(ccc_hdl) is str:
        ccc_hdl = int(ccc_hdl, 16)

    ccc_hdl_ba = struct.pack('H', ccc_hdl)

    data_ba = bytearray(bd_addr)
    data_ba.extend([enable])
    data_ba.extend(ccc_hdl_ba)

    iutctl.btp_worker.send(*GATTC['cfg_indicate'], data=data_ba)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_cfg_indicate.__name__,
                  tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_CFG_INDICATE)


def gattc_notification_ev(iutctl: IutCtl, bd_addr: BleAddress,
                          ev_type, handle=None, value=None):
    logging.debug("%s %r %r", gattc_notification_ev.__name__, bd_addr,
                  ev_type)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_EV_NOTIFICATION)

    data_ba = bytearray(bd_addr)
    data_ba.extend([ev_type])

    if handle:
        data_ba.extend(struct.pack('H', handle))

    if value:
        value_ba = binascii.unhexlify(value)
        data_ba.extend(struct.pack('H', len(value_ba)))
        data_ba.extend(value_ba)

    if tuple_data[0][0:len(data_ba)] != data_ba:
        raise BTPError("Error in notification event data")


def gatt_command_rsp_succ(iutctl: IutCtl):
    logging.debug("%s", gatt_command_rsp_succ.__name__)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT)


def gatt_dec_svc_attr(data):
    """Decodes Service Attribute data from Discovery Response data.

    BTP Single Service Attribute
    0             16           32            40
    +--------------+------------+-------------+------+
    | Start Handle | End Handle | UUID Length | UUID |
    +--------------+------------+-------------+------+

    """
    hdr = '<HHB'
    hdr_len = struct.calcsize(hdr)

    start_hdl, end_hdl, uuid_len = struct.unpack_from(hdr, data)
    uuid = struct.unpack_from('%ds' % uuid_len, data, hdr_len)

    return (start_hdl, end_hdl, uuid), hdr_len + uuid_len


def gatt_dec_incl_attr(data):
    """Decodes Included Service Attribute data from Discovery Response data.

    BTP Single Included Service Attribute
    0                16
    +-----------------+-------------------+
    | Included Handle | Service Attribute |
    +-----------------+-------------------+

    """
    hdr = '<H'
    hdr_len = struct.calcsize(hdr)

    incl_hdl = struct.unpack_from(hdr, data)
    svc, svc_len = gatt_dec_svc_attr(data[hdr_len:])

    return (incl_hdl, svc), hdr_len + svc_len


def gatt_dec_chrc_attr(data):
    """Decodes Characteristic Attribute data from Discovery Response data.

    BTP Single Characteristic Attribute
    0       16             32           40            48
    +--------+--------------+------------+-------------+------+
    | Handle | Value Handle | Properties | UUID Length | UUID |
    +--------+--------------+------------+-------------+------+

    """
    hdr = '<HHBB'
    hdr_len = struct.calcsize(hdr)

    chrc_hdl, val_hdl, props, uuid_len = struct.unpack_from(hdr, data)
    uuid = struct.unpack_from('%ds' % uuid_len, data, hdr_len)

    return (chrc_hdl, val_hdl, props, uuid), hdr_len + uuid_len


def gatt_dec_desc_attr(data):
    """Decodes Descriptor Attribute data from Discovery Response data.

    BTP Single Descriptor Attribute
    0       16            24
    +--------+-------------+------+
    | Handle | UUID Length | UUID |
    +--------+-------------+------+

    """
    hdr = '<HB'
    hdr_len = struct.calcsize(hdr)

    hdl, uuid_len = struct.unpack_from(hdr, data)
    uuid = struct.unpack_from('%ds' % uuid_len, data, hdr_len)

    return (hdl, uuid), hdr_len + uuid_len


def gatt_dec_disc_rsp(data, attr_type):
    """Decodes Discovery Response data.

    BTP Discovery Response frame format
    0                  8
    +------------------+------------+
    | Attributes Count | Attributes |
    +------------------+------------+

    """
    attrs_len = len(data) - 1
    attr_cnt, attrs = struct.unpack('B%ds' % attrs_len, data)

    attrs_list = []
    offset = 0

    for x in range(attr_cnt):
        if attr_type == "service":
            attr, attr_len = gatt_dec_svc_attr(attrs[offset:])
        elif attr_type == "include":
            attr, attr_len = gatt_dec_incl_attr(attrs[offset:])
        elif attr_type == "characteristic":
            attr, attr_len = gatt_dec_chrc_attr(attrs[offset:])
        else:  # descriptor
            attr, attr_len = gatt_dec_desc_attr(attrs[offset:])

        attrs_list.append(attr)
        offset += attr_len

    return tuple(attrs_list)


def gatt_dec_read_rsp(data):
    """Decodes Read Response data.

    BTP Read Response frame format
    0              8            24
    +--------------+-------------+------+
    | ATT Response | Data Length | Data |
    +--------------+-------------+------+

    """
    hdr = '<BH'
    hdr_len = struct.calcsize(hdr)

    att_rsp, val_len = struct.unpack_from(hdr, data)
    val = struct.unpack_from('%ds' % val_len, data, hdr_len)

    return att_rsp, val


def gatt_dec_write_rsp(data):
    """Decodes Write Response data.

    BTP Write Response frame format
    0              8
    +--------------+
    | ATT Response |
    +--------------+

    """
    return ord(data)


def gattc_disc_prim_uuid_find_attrs_rsp(iutctl: IutCtl, exp_svcs,
                                        store_attrs=False):
    """Parse and find requested services from rsp

    ATTRIBUTE FORMAT (PRIMARY SERVICE) - (start handle, end handle, uuid)

    """
    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r",
                  gattc_disc_prim_uuid_find_attrs_rsp.__name__, tuple_hdr,
                  tuple_data)
    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_DISC_PRIM_UUID)

    svcs_tuple = gatt_dec_disc_rsp(tuple_data[0], "service")

    for svc in svcs_tuple:
        for exp_svc in exp_svcs:
            # Check if option expected attribute parameters match
            svc_uuid = binascii.hexlify(svc[2][0][::-1])
            if ((exp_svc[0] and exp_svc[0] != svc[0]) or
                    (exp_svc[1] and exp_svc[1] != svc[1]) or
                    (exp_svc[2] and exp_svc[2] != svc_uuid)):
                logging.debug("gatt svc not matched = %r != %r", svc, exp_svc)

                continue

            logging.debug("gatt svc matched = %r == %r", svc, exp_svc)


def gattc_disc_prim_svcs_rsp(iutctl: IutCtl, db: GattDB):
    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_disc_prim_svcs_rsp.__name__,
                  tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_DISC_PRIM_SVCS)

    svcs_tuple = gatt_dec_disc_rsp(tuple_data[0], "service")
    logging.debug("%s %r", gattc_disc_prim_svcs_rsp.__name__, svcs_tuple)

    for svc in svcs_tuple:
        start_handle = svc[0]
        end_handle = svc[1]
        uuid = btp2uuid(len(svc[2][0]), svc[2][0])

        db.attr_add(start_handle, GattPrimary(start_handle, 1, uuid,
                                              0, end_handle))


def gattc_disc_prim_uuid_rsp(iutctl: IutCtl, db: GattDB):
    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_disc_prim_uuid_rsp.__name__,
                  tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_DISC_PRIM_UUID)

    svcs_tuple = gatt_dec_disc_rsp(tuple_data[0], "service")
    logging.debug("%s %r", gattc_disc_prim_uuid_rsp.__name__, svcs_tuple)

    for svc in svcs_tuple:
        start_handle = svc[0]
        end_handle = svc[1]
        uuid = btp2uuid(len(svc[2][0]), svc[2][0])

        db.attr_add(start_handle, GattPrimary(start_handle, 1,
                                              uuid, 0, end_handle))


def gattc_find_included_rsp(iutctl: IutCtl, db: GattDB):
    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_find_included_rsp.__name__,
                  tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_FIND_INCLUDED)

    incls_tuple = gatt_dec_disc_rsp(tuple_data[0], "include")
    logging.debug("%s %r", gattc_find_included_rsp.__name__, incls_tuple)

    for incl in incls_tuple:
        att_handle = incl[0][0]
        inc_svc_handle = incl[1][0]
        end_grp_handle = incl[1][1]
        uuid = btp2uuid(len(incl[1][2][0]), incl[1][2][0])

        db.attr_add(att_handle, GattServiceIncluded(att_handle, 1, uuid, 0,
                                                    inc_svc_handle,
                                                    end_grp_handle))


def gattc_disc_all_chrc_rsp(iutctl: IutCtl, db: GattDB):
    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_disc_all_chrc_rsp.__name__,
                  tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_DISC_ALL_CHRC)

    chrcs_tuple = gatt_dec_disc_rsp(tuple_data[0], "characteristic")
    logging.debug("%s %r", gattc_disc_all_chrc_rsp.__name__, chrcs_tuple)

    for chrc in chrcs_tuple:
        handle = chrc[0]
        value_handle = chrc[1]
        props = chrc[2]
        uuid = btp2uuid(len(chrc[3][0]), chrc[3][0])

        db.attr_add(handle, GattCharacteristic(handle, 1, uuid, 0,
                                               props, value_handle))


def gattc_disc_chrc_uuid_rsp(iutctl: IutCtl, db: GattDB):
    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_disc_chrc_uuid_rsp.__name__,
                  tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_DISC_CHRC_UUID)

    chrcs_tuple = gatt_dec_disc_rsp(tuple_data[0], "characteristic")
    logging.debug("%s %r", gattc_disc_chrc_uuid_rsp.__name__, chrcs_tuple)

    for chrc in chrcs_tuple:
        handle = chrc[0]
        value_handle = chrc[1]
        props = chrc[2]
        uuid = btp2uuid(len(chrc[3][0]), chrc[3][0])

        db.attr_add(handle, GattCharacteristic(handle, 1, uuid, 0,
                                               props, value_handle))


def gattc_disc_all_desc_rsp(iutctl: IutCtl, db: GattDB):
    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_disc_all_desc_rsp.__name__,
                  tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_DISC_ALL_DESC)

    descs_tuple = gatt_dec_disc_rsp(tuple_data[0], "descriptor")
    logging.debug("%s %r", gattc_disc_all_desc_rsp.__name__, descs_tuple)

    for desc in descs_tuple:
        handle = desc[0]
        uuid = btp2uuid(len(desc[1][0]), desc[1][0])

        db.attr_add(handle, GattCharacteristicDescriptor(handle, 1,
                                                         uuid, 0, None))


att_rsp_str = {0: "No error",
               1: "Invalid handle error",
               2: "read is not permitted error",
               3: "write is not permitted error",
               5: "authentication error",
               6: "request not supported",
               7: "Invalid offset error",
               8: "authorization error",
               12: "encryption key size error",
               13: "Invalid attribute value length error",
               17: "Insufficient resources",
               128: "Application error",
               }


def gattc_read_rsp(iutctl: IutCtl, store_rsp=False, store_val=False,
                   timeout=None):
    if timeout:
        tuple_hdr, tuple_data = iutctl.btp_worker.read(timeout)
    else:
        tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_read_rsp.__name__, tuple_hdr,
                  tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT, defs.GATT_READ)

    rsp, value = gatt_dec_read_rsp(tuple_data[0])
    logging.debug("%s %r %r", gattc_read_rsp.__name__, rsp, value)

    if store_rsp or store_val:
        gatt = iutctl.stack.gatt
        gatt.clear_verify_values()
        val = binascii.hexlify(value[0]).decode().upper()

        if store_rsp:
            gatt.add_verify_values(att_rsp_str[rsp])

        if store_val:
            gatt.add_verify_values(val)


def gattc_read_long_rsp(iutctl: IutCtl, store_rsp=False, store_val=False):
    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_read_long_rsp.__name__, tuple_hdr,
                  tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT, defs.GATT_READ_LONG)

    rsp, value = gatt_dec_read_rsp(tuple_data[0])
    logging.debug("%s %r %r", gattc_read_long_rsp.__name__, rsp, value)

    if store_rsp or store_val:
        gatt = iutctl.stack.gatt
        gatt.clear_verify_values()
        val = binascii.hexlify(value[0]).decode().upper()

        if store_rsp:
            gatt.add_verify_values(att_rsp_str[rsp])

        if store_val:
            gatt.add_verify_values(val)


def gattc_read_multiple_rsp(iutctl: IutCtl, store_val=False, store_rsp=False):
    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_read_multiple_rsp.__name__,
                  tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_READ_MULTIPLE)

    rsp, values = gatt_dec_read_rsp(tuple_data[0])
    logging.debug("%s %r %r", gattc_read_multiple_rsp.__name__, rsp, values)

    if store_rsp or store_val:
        gatt = iutctl.stack.gatt
        gatt.clear_verify_values()

        if store_rsp:
            gatt.add_verify_values(att_rsp_str[rsp])

        if store_val:
            gatt.add_verify_values((binascii.hexlify(values[0])).upper())


def gattc_write_rsp(iutctl: IutCtl, store_rsp=False, timeout=None):
    if timeout:
        tuple_hdr, tuple_data = iutctl.btp_worker.read(timeout)
    else:
        tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_write_rsp.__name__, tuple_hdr,
                  tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT, defs.GATT_WRITE)

    rsp = gatt_dec_write_rsp(tuple_data[0])
    logging.debug("%s %r", gattc_write_rsp.__name__, rsp)

    if store_rsp:
        gatt = iutctl.stack.gatt
        gatt.clear_verify_values()
        gatt.add_verify_values(att_rsp_str[rsp])


def gattc_write_long_rsp(iutctl: IutCtl, store_rsp=False):
    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("%s received %r %r", gattc_write_long_rsp.__name__,
                  tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_GATT,
                  defs.GATT_WRITE_LONG)

    rsp = gatt_dec_write_rsp(tuple_data[0])
    logging.debug("%s %r", gattc_write_long_rsp.__name__, rsp)

    if store_rsp:
        gatt = iutctl.stack.gatt
        gatt.clear_verify_values()
        gatt.add_verify_values(att_rsp_str[rsp])


def l2cap_command_rsp_succ(iutctl: IutCtl, op=None):
    logging.debug("%s", l2cap_command_rsp_succ.__name__)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_L2CAP, op)


def l2cap_conn(iutctl: IutCtl, bd_addr: BleAddress, psm):
    logging.debug("%s %r %r", l2cap_conn.__name__, bd_addr,
                  psm)

    gap_wait_for_connection(iutctl)

    if type(psm) is str:
        psm = int(psm, 16)

    data_ba = bytearray(bd_addr)
    data_ba.extend(struct.pack('H', psm))

    iutctl.btp_worker.send(*L2CAP['connect'], data=data_ba)

    l2cap_conn_rsp(iutctl)


l2cap_result_str = {0: "Connection successful",
                    2: "LE_PSM not supported",
                    4: "Insufficient Resources",
                    5: "insufficient authentication",
                    6: "insufficient authorization",
                    7: "insufficient encryption key size",
                    8: "insufficient encryption",
                    9: "Invalid Source CID",
                    10: "Source CID already allocated",
                    }


def l2cap_conn_rsp(iutctl: IutCtl):
    logging.debug("%s", l2cap_conn_rsp.__name__)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_L2CAP, defs.L2CAP_CONNECT)

    chan_id = struct.unpack_from('<B', tuple_data[0])[0]

    iutctl.stack.l2cap.channels.append(chan_id)

    logging.debug("new L2CAP channel: id %r", chan_id)


def l2cap_disconn(iutctl: IutCtl, chan_id):
    logging.debug("%s %r", l2cap_disconn.__name__, chan_id)

    channels = iutctl.stack.l2cap.channels
    try:
        idx = channels.index(chan_id)
    except ValueError:
        raise BTPError("Channel with given chan_id: %r does not exists" %
                       chan_id)

    chan_id = channels[idx]

    data_ba = bytearray([chan_id])

    iutctl.btp_worker.send(*L2CAP['disconnect'], data=data_ba)

    l2cap_command_rsp_succ(iutctl, defs.L2CAP_DISCONNECT)


def l2cap_send_data(iutctl: IutCtl, chan_id, val, val_mtp=None):
    logging.debug("%s %r %r %r", l2cap_send_data.__name__, chan_id, val,
                  val_mtp)

    if val_mtp:
        val *= int(val_mtp)

    val_ba = binascii.unhexlify(bytearray(val))
    val_len_ba = struct.pack('H', len(val_ba))

    data_ba = bytearray([chan_id])
    data_ba.extend(val_len_ba)
    data_ba.extend(val_ba)

    iutctl.btp_worker.send(*L2CAP['send_data'], data=data_ba)

    l2cap_command_rsp_succ(iutctl, defs.L2CAP_SEND_DATA)


def l2cap_listen(iutctl: IutCtl, psm, transport):
    logging.debug("%s %r %r", l2cap_le_listen.__name__, psm, transport)

    if type(psm) is str:
        psm = int(psm, 16)

    data_ba = bytearray(struct.pack('H', psm))
    data_ba.extend(struct.pack('B', transport))

    iutctl.btp_worker.send(*L2CAP['listen'], data=data_ba)

    l2cap_command_rsp_succ(iutctl, defs.L2CAP_LISTEN)


def l2cap_le_listen(iutctl, psm):
    l2cap_listen(iutctl, psm, defs.L2CAP_TRANSPORT_LE)


def l2cap_connected_ev(iutctl: IutCtl):
    logging.debug("%s", l2cap_connected_ev.__name__)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_L2CAP,
                  defs.L2CAP_EV_CONNECTED)

    chan_id, psm, bd_addr_type, bd_addr = struct.unpack_from('<BHB6s',
                                                             tuple_data[0])
    logging.debug("New L2CAP connection ID:%r on PSM:%r, Addr %r Type %r",
                  chan_id, psm, bd_addr, bd_addr_type)

    channels = iutctl.stack.l2cap.channels

    # Append incoming connection only
    if chan_id not in channels:
        channels.append(chan_id)


def l2cap_disconnected_ev(iutctl: IutCtl, exp_chan_id, store=False):
    logging.debug("%s %r", l2cap_disconnected_ev.__name__, exp_chan_id)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_L2CAP,
                  defs.L2CAP_EV_DISCONNECTED)

    res, chan_id, psm, bd_addr_type, bd_addr = \
        struct.unpack_from('<HBHB6s', tuple_data[0])

    channels = iutctl.stack.l2cap.channels
    channels.remove(chan_id)

    logging.debug("L2CAP channel disconnected: id %r", chan_id)

    if chan_id != exp_chan_id:
        raise BTPError("Error in L2CAP disconnected event data")

    if store:
        iutctl.stack.l2cap.clear_verify_values()
        iutctl.stack.l2cap.add_verify_values(l2cap_result_str[res])


def l2cap_data_rcv_ev(iutctl: IutCtl, chan_id=None, store=False):
    logging.debug("%s %r %r", l2cap_data_rcv_ev.__name__, chan_id, store)

    tuple_hdr, tuple_data = iutctl.btp_worker.read()
    logging.debug("received %r %r", tuple_hdr, tuple_data)

    btp_hdr_check(tuple_hdr, defs.BTP_SERVICE_ID_L2CAP,
                  defs.L2CAP_EV_DATA_RECEIVED)

    data_hdr = '<BH'
    data_hdr_len = struct.calcsize(data_hdr)

    rcv_chan_id, data_len = struct.unpack_from(data_hdr, tuple_data[0])
    data = binascii.hexlify(struct.unpack_from('%ds' % data_len, tuple_data[0],
                                               data_hdr_len)[0])

    if chan_id and chan_id != rcv_chan_id:
        raise BTPError("Error in L2CAP data received event data")

    if store:
        iutctl.stack.l2cap.clear_verify_values()
        iutctl.stack.l2cap.add_verify_values(data)


def mesh_config_prov(iutctl: IutCtl):
    logging.debug("%s", mesh_config_prov.__name__)

    stack = iutctl.stack

    uuid = binascii.unhexlify(stack.mesh.dev_uuid)
    static_auth = binascii.unhexlify(stack.mesh.static_auth)
    output_size = stack.mesh.output_size
    output_actions = stack.mesh.output_actions
    input_size = stack.mesh.input_size
    input_actions = stack.mesh.input_actions

    data = bytearray(struct.pack("<16s16sBHBH", uuid, static_auth, output_size,
                                 output_actions, input_size, input_actions))

    iutctl.btp_worker.send_wait_rsp(*MESH['config_prov'], data=data)


def mesh_prov_node(iutctl: IutCtl):
    logging.debug("%s", mesh_config_prov.__name__)

    stack = iutctl.stack

    net_key = binascii.unhexlify(stack.mesh.net_key)
    dev_key = binascii.unhexlify(stack.mesh.dev_key)

    data = bytearray(struct.pack("<16sHBIIH16s", net_key,
                                 stack.mesh.net_key_idx, stack.mesh.flags,
                                 stack.mesh.iv_idx, stack.mesh.seq_num,
                                 stack.mesh.addr, dev_key))

    iutctl.btp_worker.send_wait_rsp(*MESH['prov_node'], data=data)


def mesh_init(iutctl: IutCtl):
    logging.debug("%s", mesh_init.__name__)

    iutctl.btp_worker.send_wait_rsp(*MESH['init'])

    stack = iutctl.stack

    stack.mesh.is_initialized = True
    if stack.mesh.iv_test_mode_autoinit:
        mesh_iv_update_test_mode(iutctl, True)


def mesh_reset(iutctl: IutCtl):
    logging.debug("%s", mesh_reset.__name__)

    iutctl.btp_worker.send_wait_rsp(*MESH['reset'])

    stack = iutctl.stack

    stack.mesh.is_provisioned.data = False
    stack.mesh.is_initialized = False


def mesh_input_number(iutctl: IutCtl, number):
    logging.debug("%s %r", mesh_input_number.__name__, number)

    if type(number) is str:
        number = int(number)

    data = bytearray(struct.pack("<I", number))

    iutctl.btp_worker.send_wait_rsp(*MESH['input_num'], data=data)


def mesh_input_string(iutctl: IutCtl, string):
    logging.debug("%s %s", mesh_input_string.__name__, string)

    data = bytearray(string)

    iutctl.btp_worker.send_wait_rsp(*MESH['input_str'], data=data)


def mesh_iv_update_test_mode(iutctl: IutCtl, enable):
    logging.debug("%s", mesh_iv_update_test_mode.__name__)

    if enable:
        data = bytearray(struct.pack("<B", 0x01))
    else:
        data = bytearray(struct.pack("<B", 0x00))

    iutctl.btp_worker.send_wait_rsp(*MESH['iv_update_test_mode'], data=data)

    iutctl.stack.mesh.is_iv_test_mode_enabled.data = True


def mesh_iv_update_toggle(iutctl: IutCtl):
    logging.debug("%s", mesh_iv_update_toggle.__name__)

    iutctl.btp_worker.send(*MESH['iv_update_toggle'])
    tuple_hdr, tuple_data = iutctl.btp_worker.read()

    if tuple_hdr.op == defs.BTP_STATUS:
        logging.info("IV Update in progress")


def mesh_net_send(iutctl: IutCtl, ttl, src, dst, payload):
    logging.debug("%s %r %r %r %r", mesh_net_send.__name__, ttl, src, dst,
                  payload)

    if ttl is None:
        ttl = 0xff  # Use default TTL
    elif isinstance(ttl, str):
        ttl = int(ttl, 16)

    if isinstance(src, str):
        src = int(src, 16)

    if isinstance(dst, str):
        dst = int(dst, 16)

    payload = binascii.unhexlify(payload)
    payload_len = len(payload)

    if payload_len > 0xff:
        raise BTPError("Payload exceeds PDU")

    data = bytearray(struct.pack("<BHHB", ttl, src, dst, payload_len))
    data.extend(payload)

    iutctl.btp_worker.send_wait_rsp(*MESH['net_send'], data=data)


def mesh_health_generate_faults(iutctl: IutCtl):
    logging.debug("%s", mesh_health_generate_faults.__name__)

    (rsp,) = iutctl.btp_worker.send_wait_rsp(*MESH['health_generate_faults'])

    hdr_fmt = '<BBB'
    hdr_len = struct.calcsize(hdr_fmt)

    (test_id, cur_faults_cnt, reg_faults_cnt) = \
        struct.unpack_from(hdr_fmt, rsp)
    (cur_faults,) = struct.unpack_from('<%ds' % cur_faults_cnt, rsp, hdr_len)
    (reg_faults,) = struct.unpack_from('<%ds' % reg_faults_cnt, rsp,
                                       hdr_len + cur_faults_cnt)

    cur_faults = binascii.hexlify(cur_faults)
    reg_faults = binascii.hexlify(reg_faults)

    return test_id, cur_faults, reg_faults


def mesh_health_clear_faults(iutctl: IutCtl):
    logging.debug("%s", mesh_health_clear_faults.__name__)

    iutctl.btp_worker.send_wait_rsp(*MESH['mesh_clear_faults'])


def mesh_lpn(iutctl: IutCtl, enable):
    logging.debug("%s %r", mesh_lpn.__name__, enable)

    if enable:
        enable = 0x01
    else:
        enable = 0x00

    data = bytearray(struct.pack("<B", enable))

    iutctl.btp_worker.send_wait_rsp(*MESH['lpn'], data=data)


def mesh_lpn_poll(iutctl: IutCtl):
    logging.debug("%s", mesh_lpn_poll.__name__)

    iutctl.btp_worker.send_wait_rsp(*MESH['lpn_poll'])


def mesh_model_send(iutctl: IutCtl, src, dst, payload):
    logging.debug("%s %r %r %r", mesh_model_send.__name__, src, dst, payload)

    if isinstance(src, str):
        src = int(src, 16)

    if isinstance(dst, str):
        dst = int(dst, 16)

    payload = binascii.unhexlify(payload)
    payload_len = len(payload)

    if payload_len > 0xff:
        raise BTPError("Payload exceeds PDU")

    data = bytearray(struct.pack("<HHB", src, dst, payload_len))
    data.extend(payload)

    iutctl.btp_worker.send_wait_rsp(*MESH['model_send'], data=data)


def mesh_lpn_subscribe(iutctl: IutCtl, address):
    logging.debug("%s %r", mesh_lpn_subscribe.__name__, address)

    if isinstance(address, str):
        address = int(address, 16)

    data = bytearray(struct.pack("<H", address))

    iutctl.btp_worker.send_wait_rsp(*MESH['lpn_subscribe'], data=data)


def mesh_lpn_unsubscribe(iutctl: IutCtl, address):
    logging.debug("%s %r", mesh_lpn_unsubscribe.__name__, address)

    if isinstance(address, str):
        address = int(address, 16)

    data = bytearray(struct.pack("<H", address))

    iutctl.btp_worker.send_wait_rsp(*MESH['lpn_unsubscribe'], data=data)


def mesh_rpl_clear(iutctl: IutCtl):
    logging.debug("%s", mesh_rpl_clear.__name__)

    iutctl.btp_worker.send_wait_rsp(*MESH['rpl_clear'])


def mesh_proxy_identity(iutctl: IutCtl):
    logging.debug("%s", mesh_proxy_identity.__name__)

    iutctl.btp_worker.send_wait_rsp(*MESH['proxy_identity'])


def mesh_out_number_action_ev(mesh, data, data_len):
    logging.debug("%s %r", mesh_out_number_action_ev.__name__, data)

    action, number = struct.unpack_from('<HI', data)

    mesh.oob_action.data = action
    mesh.oob_data.data = number


def mesh_out_string_action_ev(mesh, data, data_len):
    logging.debug("%s %r", mesh_out_string_action_ev.__name__, data)

    hdr_fmt = '<B'
    hdr_len = struct.calcsize(hdr_fmt)

    (str_len,) = struct.unpack_from(hdr_fmt, data)
    (string,) = struct.unpack_from('<%ds' % str_len, data, hdr_len)

    mesh.oob_data.data = string


def mesh_in_action_ev(mesh, data, data_len):
    logging.debug("%s %r", mesh_in_action_ev.__name__, data)

    action, size = struct.unpack('<HB', data)


def mesh_provisioned_ev(mesh, data, data_len):
    logging.debug("%s %r", mesh_provisioned_ev.__name__, data)

    mesh.is_provisioned.data = True

    if mesh.proxy_identity:
        # TODO:
        mesh_proxy_identity()


def mesh_prov_link_open_ev(mesh, data, data_len):
    logging.debug("%s %r", mesh_prov_link_open_ev.__name__, data)

    (bearer,) = struct.unpack('<B', data)

    mesh.last_seen_prov_link_state.data = ('open', bearer)


def mesh_prov_link_closed_ev(mesh, data, data_len):
    logging.debug("%s %r", mesh_prov_link_closed_ev.__name__, data)

    (bearer,) = struct.unpack('<B', data)

    mesh.last_seen_prov_link_state.data = ('closed', bearer)


def mesh_store_net_data(iutctl: IutCtl):
    iutctl.stack.mesh.net_recv_ev_store.data = True


def mesh_iv_test_mode_autoinit(iutctl: IutCtl):
    iutctl.stack.mesh.iv_test_mode_autoinit = True


def mesh_net_rcv_ev(mesh, data, data_len):
    if not mesh.net_recv_ev_store.data:
        return

    logging.debug("%s %r %r", mesh_net_rcv_ev.__name__, data, data_len)

    hdr_fmt = '<BBHHB'
    hdr_len = struct.calcsize(hdr_fmt)

    (ttl, ctl, src, dst, payload_len) = struct.unpack_from(hdr_fmt, data, 0)
    (payload,) = struct.unpack_from('<%ds' % payload_len, data, hdr_len)
    payload = binascii.hexlify(payload)

    mesh.net_recv_ev_data.data = (ttl, ctl, src, dst, payload)


def mesh_invalid_bearer_ev(mesh, data, data_len):
    logging.debug("%s %r %r", mesh_invalid_bearer_ev.__name__, data, data_len)

    hdr_fmt = '<B'
    hdr_len = struct.calcsize(hdr_fmt)

    (opcode,) = struct.unpack_from(hdr_fmt, data, 0)

    mesh.prov_invalid_bearer_rcv.data = True


def mesh_incomp_timer_exp_ev(mesh, data, data_len):
    logging.debug("%s", mesh_incomp_timer_exp_ev.__name__)

    mesh.incomp_timer_exp.data = True


MESH_EV = {
    defs.MESH_EV_OUT_NUMBER_ACTION: mesh_out_number_action_ev,
    defs.MESH_EV_OUT_STRING_ACTION: mesh_out_string_action_ev,
    defs.MESH_EV_IN_ACTION: mesh_in_action_ev,
    defs.MESH_EV_PROVISIONED: mesh_provisioned_ev,
    defs.MESH_EV_PROV_LINK_OPEN: mesh_prov_link_open_ev,
    defs.MESH_EV_PROV_LINK_CLOSED: mesh_prov_link_closed_ev,
    defs.MESH_EV_NET_RECV: mesh_net_rcv_ev,
    defs.MESH_EV_INVALID_BEARER: mesh_invalid_bearer_ev,
    defs.MESH_EV_INCOMP_TIMER_EXP: mesh_incomp_timer_exp_ev,
}


class BTPEventHandler:
    def __init__(self, iutctl: IutCtl):
        self.iutctl = iutctl

    def __call__(self, hdr, data):
        logging.debug("%s %r %r", BTPEventHandler.__name__, hdr, data)

        stack = self.iutctl.stack
        if not stack:
            logging.info("Stack not initialized")
            return False

        if hdr.svc_id == defs.BTP_SERVICE_ID_MESH:
            if hdr.op in MESH_EV and stack.mesh:
                cb = MESH_EV[hdr.op]
                cb(stack.mesh, data[0], hdr.data_len)
                return True
        elif hdr.svc_id == defs.BTP_SERVICE_ID_GAP:
            if hdr.op in GAP_EV and stack.gap:
                cb = GAP_EV[hdr.op]
                cb(stack.gap, data[0], hdr.data_len)
                return True

        # TODO: Raise BTP error instead of logging
        logging.error("Unhandled event! svc_id %s op %s", hdr.svc_id, hdr.op)
        return False
