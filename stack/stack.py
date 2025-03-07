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
from threading import Lock, Event, Timer

from pybtp.btp import GATT_CL
from stack.gap import Gap, BleAddress
from stack.gatt import Gatt
from stack.l2cap import L2CAP
from stack.mesh import Mesh
from stack.gatt_cl import GattCl

STACK = None

class Stack:
    def __init__(self):
        self._pairing_consent_cb = None
        self._passkey_confirm_cb = None
        self.gap = None
        self.gatt = None
        self.mesh = None
        self.l2cap = None
        self.gatt_cl = None

    def gap_init(self):
        self.gap = Gap()

    def gatt_init(self):
        self.gatt = Gatt()

    def l2cap_init(self):
        self.l2cap = L2CAP()

    def gatt_cl_init(self):
        self.gatt_cl = GattCl()

    def mesh_init(self, uuid, oob, output_size, output_actions, input_size,
                  input_actions, crpl_size):
        self.mesh = Mesh(uuid, oob, output_size, output_actions, input_size,
                         input_actions, crpl_size)

    def set_pairing_consent_cb(self, cb):
        self._pairing_consent_cb = cb

    def pairing_consent_cb(self, addr: BleAddress):
        if self._pairing_consent_cb:
            self._pairing_consent_cb(addr)

    def set_passkey_confirm_cb(self, cb):
        self._passkey_confirm_cb = cb

    def passkey_confirm_cb(self, addr: BleAddress, match):
        if self._passkey_confirm_cb:
            self._passkey_confirm_cb(addr, match)

    def cleanup(self):
        if self.gap:
            self.gap_init()

        if self.mesh:
            self.mesh_init(self.mesh.dev_uuid, self.mesh.static_auth,
                           self.mesh.output_size, self.mesh.output_actions,
                           self.mesh.input_size, self.mesh.input_actions,
                           self.mesh.crpl_size)

        if self.l2cap:
            self.l2cap = L2CAP()

        if self.gatt:
            self.gatt = Gatt()


def init_stack():
    global STACK

    STACK = Stack()


def cleanup_stack():
    global STACK

    STACK = None


def get_stack():
    return STACK