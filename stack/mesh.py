from threading import Timer, Event

from stack.property import Property, timeout_cb


class Mesh:
    def __init__(self, uuid, oob, output_size, output_actions, input_size,
                 input_actions, crpl_size):

        # init data
        self.dev_uuid = uuid
        self.static_auth = oob
        self.output_size = output_size
        self.output_actions = output_actions
        self.input_size = input_size
        self.input_actions = input_actions
        self.crpl_size = crpl_size

        self.oob_action = Property(None)
        self.oob_data = Property(None)
        self.is_provisioned = Property(False)
        self.is_initialized = False
        self.last_seen_prov_link_state = Property(None)
        self.prov_invalid_bearer_rcv = Property(False)

        # provision node data
        self.net_key = '0123456789abcdef0123456789abcdef'
        self.net_key_idx = 0x0000
        self.flags = 0x00
        self.iv_idx = 0x00000000
        self.seq_num = 0x00000000
        self.addr = 0x0b0c
        self.dev_key = '0123456789abcdef0123456789abcdef'

        # health model data
        self.health_test_id = Property(0x00)
        self.health_current_faults = Property(None)
        self.health_registered_faults = Property(None)

        # vendor model data
        self.vendor_model_id = '0002'

        # IV update
        self.iv_update_timeout = Property(120)
        self.is_iv_test_mode_enabled = Property(False)
        self.iv_test_mode_autoinit = False

        # Network
        # net_recv_ev_store - store data for further verification
        self.net_recv_ev_store = Property(False)
        # net_recv_ev_data (ttl, ctl, src, dst, payload)
        self.net_recv_ev_data = Property(None)
        self.incomp_timer_exp = Property(False)

        # LPN
        self.lpn_subscriptions = []

        # Node Identity
        self.proxy_identity = False

    def proxy_identity_enable(self):
        self.proxy_identity = True

    def wait_for_incomp_timer_exp(self, timeout):
        if self.incomp_timer_exp.data:
            return True

        flag = Event()
        flag.set()

        t = Timer(timeout, timeout_cb, [flag])
        t.start()

        while flag.is_set():
            if self.incomp_timer_exp.data:
                t.cancel()
                return True

        return False
