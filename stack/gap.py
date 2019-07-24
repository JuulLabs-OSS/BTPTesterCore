import logging
from asyncio import Event
from collections import namedtuple
from threading import Timer

from pybtp.types import addr2btp_ba
from stack.property import Property, timeout_cb

LeAdv = namedtuple('LeAdv', 'addr rssi flags eir')


class BleAddress:
    def __init__(self, addr: str, addr_type: int):
        addr = addr.lower()

        self._addr_type = addr_type
        self._addr = addr

    @property
    def addr(self):
        return self._addr

    @property
    def addr_type(self):
        return self._addr_type

    def __eq__(self, other):
        return ((self.addr_type == other.addr_type) and
                (self.addr == other.addr))

    def __hash__(self):
        return self.addr.__hash__()

    def __repr__(self):
        return "(%r %r)" % (self._addr_type, self._addr)

    def __str__(self):
        return self.__repr__()

    def __iter__(self):
        return self.__bytes__().__iter__()

    def __bytes__(self):
        data_ba = bytearray()
        bd_addr_ba = addr2btp_ba(self.addr)

        data_ba.extend([self.addr_type])
        data_ba.extend(bd_addr_ba)
        return data_ba


class ConnParams:
    def __init__(self, conn_itvl, conn_latency, supervision_timeout):
        self.conn_itvl = conn_itvl
        self.conn_latency = conn_latency
        self.supervision_timeout = supervision_timeout


class Connection:
    def __init__(self, addr: BleAddress):
        self.addr = addr


class Gap:
    def __init__(self):
        self.name = None
        self.name_short = None

        self.connections = Property({})
        self.current_settings = Property({
            "Powered": False,
            "Connectable": False,
            "Fast Connectable": False,
            "Discoverable": False,
            "Bondable": False,
            "Link Level Security": False,  # Link Level Security (Sec. mode 3)
            "SSP": False,  # Secure Simple Pairing
            "BREDR": False,  # Basic Rate/Enhanced Data Rate
            "HS": False,  # High Speed
            "LE": False,  # Low Energy
            "Advertising": False,
            "SC": False,  # Secure Connections
            "Debug Keys": False,
            "Privacy": False,
            "Controller Configuration": False,
            "Static Address": False,
        })
        self.iut_bd_addr = Property({
            "address": None,
            "type": None,
        })
        self.discoverying = Property(False)
        self.found_devices = Property([])  # List of found devices

        self.passkey = Property(None)
        self.conn_params = Property(None)

    def connected(self, addr: BleAddress):
        self.connections.data[addr] = Connection(addr)

    def disconnected(self, addr: BleAddress):
        self.connections.data.pop(addr)

    def is_connected(self, addr: BleAddress = None):
        if not addr:
            return len(self.connections.data) > 0
        conn = self.connections.data.get(addr, None)
        return conn is not None

    def wait_for_connection(self, timeout, addr: BleAddress = None):
        if self.is_connected(addr):
            return True

        flag = Event()
        flag.set()

        t = Timer(timeout, timeout_cb, [flag])
        t.start()

        while flag.is_set():
            if self.is_connected(addr):
                t.cancel()
                return True

        return False

    def wait_for_disconnection(self, timeout, addr: BleAddress = None):
        if not self.is_connected(addr):
            return True

        flag = Event()
        flag.set()

        t = Timer(timeout, timeout_cb, [flag])
        t.start()

        while flag.is_set():
            if not self.is_connected(addr):
                t.cancel()
                return True

        return False

    def current_settings_set(self, key):
        if key in self.current_settings.data:
            self.current_settings.data[key] = True
        else:
            logging.error("%s %s not in current_settings",
                          self.current_settings_set.__name__, key)

    def current_settings_clear(self, key):
        if key in self.current_settings.data:
            self.current_settings.data[key] = False
        else:
            logging.error("%s %s not in current_settings",
                          self.current_settings_clear.__name__, key)

    def current_settings_get(self, key):
        if key in self.current_settings.data:
            return self.current_settings.data[key]
        else:
            logging.error("%s %s not in current_settings",
                          self.current_settings_get.__name__, key)
            return False

    def iut_addr_get(self) -> BleAddress:
        return self.iut_bd_addr

    def iut_addr_get_str(self) -> str:
        return self.iut_bd_addr.addr

    def iut_addr_get_type(self) -> int:
        return self.iut_bd_addr.addr_type

    def iut_addr_set(self, addr: BleAddress):
        self.iut_bd_addr = addr

    def iut_has_privacy(self):
        return self.current_settings_get("Privacy")

    def set_conn_params(self, params):
        self.conn_params.data = params

    def get_conn_params(self):
        return self.conn_params.data

    def reset_discovery(self):
        self.discoverying.data = True
        self.found_devices.data = []

    def get_passkey(self, timeout=5):
        if self.passkey.data is None:
            flag = Event()
            flag.set()

            t = Timer(timeout, timeout_cb, [flag])
            t.start()

            while flag.is_set():
                if self.passkey.data:
                    t.cancel()
                    break

        return self.passkey.data
