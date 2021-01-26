import logging
import threading
from collections import defaultdict
from concurrent.futures.thread import ThreadPoolExecutor

import dbus
import dbus.mainloop.glib

from pybtp.utils import wait_futures
from testcases.utils import EV_TIMEOUT

BLUEZ_SERVICE = "org.bluez"
ADAPTER_INTERFACE = BLUEZ_SERVICE + ".Adapter1"
DEVICE_INTERFACE = BLUEZ_SERVICE + ".Device1"
GATT_SERVICE_IFACE = BLUEZ_SERVICE + ".GattService1"
GATT_CHRC_IFACE = BLUEZ_SERVICE + ".GattCharacteristic1"
DEVICE_ADDR = 'C0:FA:AC:CF:FA:0A'
INTERFACES_ADDED = 'InterfacesAdded'
INTERFACES_REMOVED = 'InterfacesRemoved'
PROPERTIES_CHANGED = 'PropertiesChanged'
COAP_REQUEST_CHAR_UUID = 'AD7B334F-4637-4B86-90B6-9D787F03D218'
COAP_RESPONSE_CHAR_UUID = 'E9241982-4580-42C4-8831-95048216B256'


def get_managed_objects(bus):
    manager = dbus.Interface(bus.get_object("org.bluez", "/"),
                             "org.freedesktop.DBus.ObjectManager")
    return manager.GetManagedObjects()


def find_adapter(bus, pattern=None):
    return find_adapter_in_objects(bus, get_managed_objects(bus), pattern)


def find_adapter_in_objects(bus, objects, pattern=None):
    for path, ifaces in objects.items():
        adapter = ifaces.get(ADAPTER_INTERFACE)
        if adapter is None:
            continue
        if not pattern or pattern == adapter["Address"] or \
                path.endswith(pattern):
            obj = bus.get_object(BLUEZ_SERVICE, path)
            return dbus.Interface(obj, ADAPTER_INTERFACE)
    return None


def find_device(bus, device_address, adapter_pattern=None):
    return find_device_in_objects(bus, get_managed_objects(bus), device_address,
                                  adapter_pattern)


def find_device_in_objects(bus, objects, device_address, adapter_pattern=None):
    path_prefix = ""
    if adapter_pattern:
        adapter = find_adapter_in_objects(bus, objects, adapter_pattern)
        if not adapter:
            return None
        path_prefix = adapter.object_path
    for path, ifaces in objects.items():
        device = ifaces.get(DEVICE_INTERFACE)
        if device is None:
            continue
        if (device["Address"] == device_address and
                path.startswith(path_prefix)):
            obj = bus.get_object(BLUEZ_SERVICE, path)
            return dbus.Interface(obj, DEVICE_INTERFACE), device
    return None, None


def find_characteristic(bus, device_path, uuid):
    return find_characteristic_in_objects(bus, get_managed_objects(bus),
                                          device_path, uuid)


def find_characteristic_in_objects(bus, objects, device_path, uuid):
    for path, ifaces in objects.items():
        char = ifaces.get(GATT_CHRC_IFACE)
        if char is None:
            continue

        if path.startswith(device_path) and \
                char["UUID"].lower() == uuid.lower():
            obj = bus.get_object(BLUEZ_SERVICE, path)
            return dbus.Interface(obj, GATT_CHRC_IFACE), char
    return None, None


class DBusEventListener:
    def __init__(self, verify_f):
        self._sem = threading.Semaphore(value=0)
        self._verify_f = verify_f
        self._result = None

    def acquire(self):
        self._sem.acquire()
        return self._result

    def release(self):
        self._sem.release()

    def verify(self, args):
        if self._verify_f:
            return_val = self._verify_f(args)
            if return_val:
                self._result = args
            return return_val
        else:
            self._result = args
        return True


class DBusEventHandler:
    def __init__(self):
        self.listeners = defaultdict(list)
        self.executor = ThreadPoolExecutor()

    def wait_for_event(self, signal_name, f):
        logging.debug("%s %r %r", self.wait_for_event, signal_name, f)
        listener = DBusEventListener(f)
        self.listeners[signal_name].append(listener)
        return self.executor.submit(listener.acquire)

    def __call__(self, signal_name, data):
        logging.debug("%s %r", DBusEventHandler.__name__, signal_name)

        listeners = self.listeners[signal_name]
        to_remove = []
        for listener in listeners:
            if listener.verify(data):
                listener.release()
                to_remove.append(listener)

        self.listeners[signal_name] = list(set(listeners) - set(to_remove))
        return True


class CoapProxy():
    def __init__(self, dev_addr, adapter_id):
        self.dev_addr = dev_addr
        self.adapter_id = adapter_id

        self.bus = dbus.SystemBus()

        self.bus.add_signal_receiver(self._properties_changed,
                                     bus_name="org.bluez",
                                     dbus_interface="org.freedesktop.DBus.Properties",
                                     signal_name="PropertiesChanged",
                                     path_keyword="path")

        self.bus.add_signal_receiver(self._interfaces_added,
                                     bus_name="org.bluez",
                                     dbus_interface="org.freedesktop.DBus.ObjectManager",
                                     signal_name="InterfacesAdded")

        self.bus.add_signal_receiver(self._interfaces_removed,
                                     bus_name="org.bluez",
                                     dbus_interface="org.freedesktop.DBus.ObjectManager",
                                     signal_name="InterfacesRemoved")
        self._ev_handler = DBusEventHandler()
        self.adapter = None
        self.device_iface = None
        self.device_props = None
        self.req_char_iface = None
        self.req_char_props = None
        self.rsp_char_iface = None
        self.rsp_char_props = None
        super().__init__()

    def run(self):
        self.device_iface, self.device_props = find_device(self.bus,
                                                           self.dev_addr,
                                                           self.adapter_id)

        if not self.device_iface:
            future = self._ev_handler.wait_for_event(INTERFACES_ADDED,
                                                     self._device_added)
            adapter = find_adapter(self.bus, self.adapter_id)
            adapter.StartDiscovery()
            wait_futures([future], timeout=EV_TIMEOUT)
            adapter.StopDiscovery()
            self.device_iface, self.device_props = find_device(self.bus,
                                                               self.dev_addr,
                                                               self.adapter_id)

        if not self.device_props.get('ServicesResolved', None):
            future = self._ev_handler.wait_for_event(PROPERTIES_CHANGED,
                                                     self._device_found)
            adapter = find_adapter(self.bus, self.adapter_id)
            adapter.StartDiscovery()
            wait_futures([future], timeout=EV_TIMEOUT)
            adapter.StopDiscovery()
            self.device_iface, self.device_props = find_device(self.bus,
                                                               self.dev_addr,
                                                               self.adapter_id)

            future = self._ev_handler.wait_for_event(PROPERTIES_CHANGED,
                                                     self._device_connected)
            self.device_iface.Connect()
            wait_futures([future], timeout=EV_TIMEOUT)

            self.device_iface, self.device_props = find_device(self.bus,
                                                               self.dev_addr,
                                                               self.adapter_id)

        logging.debug('Connected')

        self.req_char_iface, self.req_char_props = \
            find_characteristic(self.bus,
                                self.device_iface.object_path,
                                COAP_REQUEST_CHAR_UUID)

        if not self.req_char_iface:
            logging.debug("Couldn't find CoAP Request characteristic")
            return

        self.rsp_char_iface, self.rsp_char_props = \
            find_characteristic(self.bus,
                                self.device_iface.object_path,
                                COAP_RESPONSE_CHAR_UUID)

        if not self.rsp_char_iface:
            logging.debug("Couldn't find CoAP Response characteristic")
            return

        self.rsp_char_iface.StartNotify()

        logging.debug('Device ready')
        return 0

    def is_ready(self):
        return self.req_char_iface and self.rsp_char_iface

    def send(self, data):
        if not self.is_ready():
            return False

        future = self._ev_handler.wait_for_event(PROPERTIES_CHANGED,
                                                 self._notification_received)
        self.req_char_iface.WriteValue(data, {})
        wait_futures([future], timeout=10)
        result = future.result()
        response = bytes(result[1]["Value"])
        return response

    def _notification_received(self, args):
        interface, changed, invalidated, path = args
        if path != self.rsp_char_iface.object_path or \
                interface != GATT_CHRC_IFACE:
            return False

        logging.debug("Properties changed for characteristic %s %s",
                      path, changed)

        return changed.get("Value", None)

    def _device_connected(self, args):
        interface, changed, invalidated, path = args
        if path != self.device_iface.object_path or \
                interface != DEVICE_INTERFACE:
            return False

        logging.debug("Properties changed for device %s %s", path, changed)

        connected = changed.get("ServicesResolved", None)
        return connected

    def _device_disconnected(self, args):
        interface, changed, invalidated, path = args
        if path != self.device_iface.object_path or \
                interface != DEVICE_INTERFACE:
            return False

        logging.debug("Properties changed for device %s %s", path, changed)
        return

    def _device_added(self, args):
        logging.debug("%s", self._device_found)
        path, interfaces = args
        properties = interfaces.get(DEVICE_INTERFACE)
        address = properties["Address"]
        return address == self.dev_addr

    def _device_found(self, args):
        logging.debug("%s", self._device_found)
        interface, changed, invalidated, path = args
        if path != self.device_iface.object_path or \
                interface != DEVICE_INTERFACE:
            return False

        logging.debug("Properties changed for device %s %s", path, changed)

        return changed.get("RSSI", None)

    def _interfaces_added(self, path, interfaces):
        logging.debug("%s %s", self._interfaces_added, path)

        self._ev_handler(INTERFACES_ADDED, (path, interfaces))

    def _interfaces_removed(self, path, interfaces):
        logging.debug("%s %s", self._interfaces_removed, path)

        self._ev_handler(INTERFACES_REMOVED, (path, interfaces))

    def _properties_changed(self, interface, changed, invalidated, path):
        logging.debug("%s %s", self._properties_changed, path)

        self._ev_handler(PROPERTIES_CHANGED, (interface, changed,
                                              invalidated, path))
