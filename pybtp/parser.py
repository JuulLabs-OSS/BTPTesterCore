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

import struct

from collections import namedtuple
import logging

HDR_LEN = 5


def parse_svc_gap(op, data_len, data):
    pass


def dec_hdr(binary):
    """Decode BTP frame header

    BTP header format
    0            8       16                 24            40
    +------------+--------+------------------+-------------+
    | Service ID | Opcode | Controller Index | Data Length |
    +------------+--------+------------------+-------------+

    """
    logging.debug("%s, %r", dec_hdr.__name__, binary)

    Header = namedtuple('Header', 'svc_id op ctrl_index data_len')

    hdr = Header._make(struct.unpack("<BBBH", binary))

    return hdr


def dec_data(binary):
    logging.debug("%s, %r", dec_data.__name__, binary)

    data_len = len(binary)
    data = struct.unpack('<%ds' % data_len, binary)

    return data


def enc_frame(svc_id, op, ctrl_index, data):
    logging.debug("%s, %r %r %r %r",
                  enc_frame.__name__, svc_id, op, ctrl_index, data)

    str_data = bytearray(data)
    int_len = len(str_data)
    hex_len = struct.pack('h', int_len)
    binary = struct.pack('<BBB2s%ds' % int_len, svc_id, op, ctrl_index, hex_len,
                         str_data)

    return binary
