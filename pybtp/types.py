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

from pybtp import defs

from binascii import unhexlify

gap_settings_btp2txt = {
    defs.GAP_SETTINGS_POWERED: "Powered",
    defs.GAP_SETTINGS_CONNECTABLE: "Connectable",
    defs.GAP_SETTINGS_FAST_CONNECTABLE: "Fast Connectable",
    defs.GAP_SETTINGS_DISCOVERABLE: "Discoverable",
    defs.GAP_SETTINGS_BONDABLE: "Bondable",
    defs.GAP_SETTINGS_LINK_SEC_3: "Link Level Security",
    defs.GAP_SETTINGS_SSP: "SSP",
    defs.GAP_SETTINGS_BREDR: "BREDR",
    defs.GAP_SETTINGS_HS: "HS",
    defs.GAP_SETTINGS_LE: "LE",
    defs.GAP_SETTINGS_ADVERTISING: "Advertising",
    defs.GAP_SETTINGS_SC: "SC",
    defs.GAP_SETTINGS_DEBUG_KEYS: "Debug Keys",
    defs.GAP_SETTINGS_PRIVACY: "Privacy",
    defs.GAP_SETTINGS_CONTROLLER_CONFIG: "Controller Configuration",
    defs.GAP_SETTINGS_STATIC_ADDRESS: "Static Address",
}


def addr2btp_ba(addr_str):
    return unhexlify("".join(addr_str.split(':')).encode())[::-1]


class BTPError(Exception):
    """Exception raised if BTP error occurs.

    If this exception is raised the status of the running test case is updated
    accordingly to show that BTP error has occurred.

    """
    pass


class SynchError(Exception):
    """Exception raised if cannot synchronize"""
    pass

class AdType:
    flags = 0x01
    uuid16_some = 0x02
    uuid16_full = 0x03
    uuid32_some = 0x04
    uuid32_full = 0x05
    uuid128_some = 0x06
    uuid128_full = 0x07
    name_short = 0x08
    name_full = 0x09
    tx_power = 0x0a
    cod = 0x0d
    uuid16_svc_solicit = 0x14
    uuid16_svc_data = 0x16
    gap_appearance = 0x19
    manufacturer_data = 0xff


class AdFlags:
    le_limit_discov_mode = 0x01
    le_gen_discov_mode = 0x02
    br_edr_not_supp = 0x04
    sim_le_br_edr_contr = 0x08
    sim_le_br_edr_host = 0x10


class UUID:
    primary_svc = '2800'
    secondary_svc = '2801'
    include_svc = '2802'
    chrc = '2803'
    gap_svc = '1800'
    gatt_svc = '1801'
    CEP = '2900'
    CUD = '2901'
    CCC = '2902'
    SCC = '2903'
    CPF = '2904'
    CAF = '2905'
    device_name = '2A00'
    appearance = '2A01'
    service_changed = '2A05'
    battery_level = '2A19'
    date_of_birth = '2A85'
    gender = '2A8C'
    VND16_1 = 'AA50'
    VND16_2 = 'AA51'
    VND16_3 = 'AA52'
    VND16_4 = 'AA53'
    VND16_5 = 'AA54'
    VND128_1 = 'F000BB5004514000B123456789ABCDEF'
    VND128_2 = 'F000BB5104514000B123456789ABCDEF'
    VND128_3 = 'F000BB5204514000B123456789ABCDEF'


def hdl_str(hdl):
    return '{0:x}'.format(hdl, 'x')


def u16_hdl_str(hdl):
    return '{0:04x}'.format(hdl, 'x')


def u16_hdl_uc_str(hdl):
    return '{0:04x}'.format(hdl, 'X')


class PTS_DB:
    PTS_UUID_FMT = '0000{}8C26476F89A7A108033A69C7'
    SVC = PTS_UUID_FMT.format('0001')
    CHR_NO_PERM = PTS_UUID_FMT.format('0002')
    CHR_READ = PTS_UUID_FMT.format('0003')
    CHR_RELIABLE_WRITE = PTS_UUID_FMT.format('0004')
    CHR_WRITE_NO_RSP = PTS_UUID_FMT.format('0005')
    CHR_READ_WRITE = PTS_UUID_FMT.format('0006')
    CHR_READ_WRITE_ENC = PTS_UUID_FMT.format('0007')
    CHR_READ_WRITE_AUTHEN = PTS_UUID_FMT.format('0008')
    CHR_READ_WRITE_AUTHOR = PTS_UUID_FMT.format('0009')
    DSC_READ = PTS_UUID_FMT.format('000A')
    DSC_WRITE = PTS_UUID_FMT.format('000B')
    DSC_READ_WRITE = PTS_UUID_FMT.format('000C')
    DSC_READ_WRITE_ENC = PTS_UUID_FMT.format('000D')
    DSC_READ_WRITE_AUTHEN = PTS_UUID_FMT.format('000E')
    INC_SVC = PTS_UUID_FMT.format('000F')
    CHR_READ_WRITE_ALT = PTS_UUID_FMT.format('0010')

    CHR_NO_PERM_ID = 0
    CHR_READ_ID = 1
    CHR_RELIABLE_WRITE_ID = 2
    CHR_WRITE_NO_RSP_ID = 3
    CHR_READ_WRITE_ID = 4
    CHR_READ_WRITE_ENC_ID = 5
    CHR_READ_WRITE_AUTHEN_ID = 6
    CHR_READ_WRITE_AUTHOR_ID = 7
    DSC_READ_ID = 8
    DSC_WRITE_ID = 9
    DSC_READ_WRITE_ID = 10
    DSC_READ_WRITE_ENC_ID = 11
    DSC_READ_WRITE_AUTHEN_ID = 12
    CHR_READ_WRITE_ALT_ID = 13

    iut_attr_db_off = 26

    SVC_HDL = u16_hdl_str(iut_attr_db_off + 0)
    CHR_NO_PERM_HDL = u16_hdl_str(iut_attr_db_off + 2)
    CHR_READ_HDL = u16_hdl_str(iut_attr_db_off + 4)
    CHR_RELIABLE_WRITE_HDL = u16_hdl_str(iut_attr_db_off + 7)
    CHR_WRITE_NO_RSP_HDL = u16_hdl_str(iut_attr_db_off + 9)
    CHR_READ_WRITE_HDL = hdl_str(iut_attr_db_off + 11)
    CHR_READ_WRITE_ENC_HDL = u16_hdl_str(iut_attr_db_off + 14)
    CHR_READ_WRITE_AUTHEN_HDL = u16_hdl_str(iut_attr_db_off + 16)
    CHR_READ_WRITE_AUTHOR_HDL = u16_hdl_str(iut_attr_db_off + 18)
    DSC_READ_HDL = u16_hdl_str(iut_attr_db_off + 19)
    DSC_WRITE_HDL = u16_hdl_str(iut_attr_db_off + 20)
    DSC_READ_WRITE_HDL = u16_hdl_str(iut_attr_db_off + 21)
    DSC_READ_WRITE_ENC_HDL = u16_hdl_str(iut_attr_db_off + 22)
    DSC_READ_WRITE_AUTHEN_HDL = u16_hdl_str(iut_attr_db_off + 23)
    SVC_END_HDL = u16_hdl_str(iut_attr_db_off + 23)
    INC_SVC_HDL = u16_hdl_str(iut_attr_db_off + 25)
    CHR_READ_WRITE_ALT_HDL = u16_hdl_str(iut_attr_db_off + 27)


class IOCap:
    display_only = 0
    display_yesno = 1
    keyboard_only = 2
    no_input_output = 3
    keyboard_display = 4


class Addr:
    le_public = 0
    le_random = 1


class MeshVals:
    subscription_addr_list1 = 'C302'


def decode_flag_name(flag, names_dict):
    """Returns string description that corresponds to flag"""

    decoded_str = ""
    sep = ", "

    for named_flag in sorted(names_dict.keys()):
        if (flag & named_flag) == named_flag:
            decoded_str += names_dict[named_flag] + sep

    if decoded_str.endswith(sep):
        decoded_str = decoded_str.rstrip(sep)

    return decoded_str


class Prop:
    """Properties of characteresic

    Specified in BTP spec:

    Possible values for the Properties parameter are a bit-wise of the
    following bits:

    0       Broadcast
    1       Read
    2       Write Without Response
    3       Write
    4       Notify
    5       Indicate
    6       Authenticated Signed Writes
    7       Extended Properties

    """
    broadcast = 2 ** 0
    read = 2 ** 1
    write_wo_resp = 2 ** 2
    write = 2 ** 3
    nofity = 2 ** 4
    indicate = 2 ** 5
    auth_swrite = 2 ** 6
    ext_prop = 2 ** 7

    names = {
        broadcast: "Broadcast",
        read: "Read",
        write_wo_resp: "Write Without Response",
        write: "Write",
        nofity: "Notify",
        indicate: "Indicate",
        auth_swrite: "Authenticated Signed Writes",
        ext_prop: "Extended Properties",
    }

    @staticmethod
    def decode(prop):
        return decode_flag_name(prop, Prop.names)


class Perm:
    """Permission of characteresic or descriptor

    Specified in BTP spec:

    Possible values for the Permissions parameter are a bit-wise of the
    following bits:

    0       Read
    1       Write
    2       Read with Encryption
    3       Write with Encryption
    4       Read with Authentication
    5       Write with Authentication
    6       Authorization

    """
    read = 2 ** 0
    read_enc = 2 ** 1
    read_enc_mitm_ = 2 ** 2
    write = 2 ** 4
    write_enc = 2 ** 5
    read_authn = 2 ** 5
    write_authn = 2 ** 5
    read_authz = 2 ** 6
    write_authz = 2 ** 7

    names = {
        read: "Read",
        write: "Write",
        read_enc: "Read with Encryption",
        write_enc: "Write with Encryption",
        read_authn: "Read with Authentication",
        write_authn: "Write with Authentication",
        read_authz: "Read with Authorization",
        write_authz: "Write with Authorization"
    }

    @staticmethod
    def decode(perm):
        return decode_flag_name(perm, Perm.names)
