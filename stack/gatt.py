from asyncio import Event


class Gatt:
    def __init__(self):
        self.verify_values = []
        self.svcs = []
        self.chrs = []
        self.gatt_db = {}

    # These definitions are for PTS compatibility

    def add_verify_values(self, val):
        self.verify_values.append(val)

    def clear_verify_values(self):
        self.verify_values.clear()

    def add_svcs(self, val):
        self.svcs.append(val)

    def clear_svcs(self):
        self.svcs.clear()

    def add_chrs(self, val):
        self.chrs.append(val)

    def clear_chrs(self):
        self.chrs.clear()

    # End

    def add_attribute(self, attr_type, values):
        handle = values[0]
        self.gatt_db[handle] = (attr_type, values)

    def clear_db(self):
        self.gatt_db.clear()

    def print_db(self):
        for hdl, attr in sorted(self.gatt_db.items()):
            (attr_type, value) = attr
            print("{} {} {!r}".format(hdl, attr_type, value))

    def find_characteristic_end(self, hdl):
        attr = self.gatt_db.get(hdl)
        (attr_type, value) = attr
        if attr_type != "characteristic":
            raise Exception("Not a characteristic handle")

        handles = list(sorted(self.gatt_db.keys()))
        for next_hdl in handles:
            # Find next attribute handle
            if next_hdl <= hdl:
                continue

            # if the next handle is equal to the previous characteristic
            # definition + 2, then it means there are no descriptors there
            if next_hdl == (hdl + 2):
                return None

            attr = self.gatt_db.get(next_hdl)
            (attr_type, value) = attr

            # find the next attribute that is not a descriptor,
            # this will be the end of the characteristic
            if attr_type == "descriptor":
                continue

            # Return handle of the next attribue - 1, which is the end
            # of the previous characteristic
            return next_hdl - 1

        # If there are no more characteristics then return 0xffff
        return 0xffff


class GattAttribute:
    def __init__(self, handle, perm, uuid, att_rsp):
        self.handle = handle
        self.perm = perm
        self.uuid = uuid
        self.att_read_rsp = att_rsp

    def __repr__(self):
        return "{}({} {} {} {})".format(self.__class__.__name__,
                                        self.handle, self.perm,
                                        self.uuid, self.att_read_rsp)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False

        return self.handle == other.handle and self.uuid == other.uuid

    def __ne__(self, other):
        return not self == other


class GattService(GattAttribute):
    def __init__(self, handle, perm, uuid, att_rsp, end_hdl):
        GattAttribute.__init__(self, handle, perm, uuid, att_rsp)
        self.end_hdl = end_hdl

    def __repr__(self):
        return "{}({})".format(super(GattService, self).__repr__(),
                               self.end_hdl)


class GattPrimary(GattService):
    pass


class GattSecondary(GattService):
    pass


class GattServiceIncluded(GattAttribute):
    def __init__(self, handle, perm, uuid, att_rsp, incl_svc_hdl, end_grp_hdl):
        GattAttribute.__init__(self, handle, perm, uuid, att_rsp)
        self.incl_svc_hdl = incl_svc_hdl
        self.end_grp_hdl = end_grp_hdl

    def __repr__(self):
        return "{}({} {})".format(super(GattServiceIncluded, self).__repr__(),
                                  self.incl_svc_hdl,
                                  self.end_grp_hdl)

    def __eq__(self, other):
        if self.__class__ != other.__class__:
            return False

        return self.handle == other.handle and \
               self.incl_svc_hdl == other.incl_svc_hdl and \
               self.end_grp_hdl == other.end_grp_hdl

    def __ne__(self, other):
        return not self == other


class GattCharacteristic(GattAttribute):
    def __init__(self, handle, perm, uuid, att_rsp, prop, value_handle):
        GattAttribute.__init__(self, handle, perm, uuid, att_rsp)
        self.prop = prop
        self.value_handle = value_handle

    def __repr__(self):
        return "{}({} {})".format(super(GattCharacteristic, self).__repr__(),
                                  self.prop, self.value_handle)


class GattCharacteristicDescriptor(GattAttribute):
    def __init__(self, handle, perm, uuid, att_rsp, value):
        GattAttribute.__init__(self, handle, perm, uuid, att_rsp)
        self.value = value
        self.has_changed = Event()

    def __repr__(self):
        return "{}({})".format(super(GattCharacteristicDescriptor,
                                     self).__repr__(),
                               self.value)


class GattValue:
    def __init__(self):
        self._att_rsp = None
        self._val = None

    @property
    def value(self):
        return self._val

    @value.setter
    def value(self, new_val):
        self._val = new_val

    @property
    def att_rsp(self):
        return self._att_rsp

    @att_rsp.setter
    def att_rsp(self, new_val):
        self._att_rsp = new_val


class GattDB:
    def __init__(self):
        self.db = dict()

    def clear(self):
        self.db.clear()

    def attr_add(self, handle, attr):
        self.db[handle] = attr

    def attr_lookup_handle(self, handle):
        if handle in self.db:
            return self.db[handle]
        else:
            return None

    def find_svc_by_uuid(self, uuid):
        for hdl, attr in sorted(self.db.items()):
            if not isinstance(attr, GattService):
                continue

            if attr.uuid == uuid:
                return attr

        return None

    def find_inc_svc_by_uuid(self, uuid):
        for hdl, attr in sorted(self.db.items()):
            if not isinstance(attr, GattServiceIncluded):
                continue

            if attr.uuid == uuid:
                return attr

        return None

    def find_chr_by_uuid(self, uuid):
        for hdl, attr in sorted(self.db.items()):
            if not isinstance(attr, GattCharacteristic):
                continue

            if attr.uuid == uuid:
                return attr

        return None

    def find_dsc_by_uuid(self, uuid):
        for hdl, attr in sorted(self.db.items()):
            if not isinstance(attr, GattCharacteristicDescriptor):
                continue

            if attr.uuid == uuid:
                return attr

        return None

    # Return a list of attributes sorted by handle
    def get_attributes(self):
        return [attr[1] for attr in sorted(self.db.items())]

    # Return a list of services sorted by handle
    def get_services(self):
        return [attr[1] for attr in
                filter(lambda attr: isinstance(attr[1], GattService),
                       sorted(self.db.items()))]

    # Return a list of services sorted by handle
    def get_characteristics(self):
        return [attr[1] for attr in
                filter(lambda attr: isinstance(attr[1], GattCharacteristic),
                       sorted(self.db.items()))]

    # Return a list of descriptors sorted by handle
    def get_descriptors(self):
        return [attr[1] for attr in
                filter(lambda attr: isinstance(attr[1],
                                               GattCharacteristicDescriptor),
                       sorted(self.db.items()))]

    def find_characteristic_end(self, hdl):
        attr = self.db.get(hdl)
        if not isinstance(attr, GattCharacteristic):
            raise Exception("Not a characteristic handle")

        handles = list(sorted(self.db.keys()))
        for next_hdl in handles:
            # Find next attribute handle
            if next_hdl <= hdl:
                continue

            # if the next handle is equal to the previous characteristic
            # definition + 2, then it means there are no descriptors there
            if next_hdl == (hdl + 2):
                return None

            attr = self.db.get(next_hdl)

            # find the next attribute that is not a descriptor,
            # this will be the end of the characteristic
            if isinstance(attr, GattCharacteristicDescriptor):
                continue

            # Return handle of the next attribue - 1, which is the end
            # of the previous characteristic
            return next_hdl - 1

        # If there are no more characteristics then return 0xffff
        return 0xffff

    def print_db(self):
        for hdl, attr in sorted(self.db.items()):
            print("{} {!r}".format(hdl, attr))

    def contains(self, other):
        return other.db.items() <= self.db.items()

    def __eq__(self, other):
        if not isinstance(other, GattDB):
            return False
        return self.db == other.db

    def __ne__(self, other):
        return not self == other

    def __len__(self):
        return len(self.db)
