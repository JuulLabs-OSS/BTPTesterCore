import subprocess

from stack.gap import BleAddress


def get_controller_address(index):
    cmd = 'hcitool dev | grep hci{} | cut -f3'.format(index)
    addr = subprocess.check_output(cmd, shell=True).strip().decode().replace(':', '')
    return addr


class TesterConfig:
    def __init__(self, hci_index):
        self._address = get_controller_address(hci_index)
        self.tester_addr = BleAddress(self._address, 0)
        self.tester_read_hdl = '0x0003'
        self.tester_write_hdl = '0x0005'
        self.tester_service_uuid = '180f'
        self.tester_passkey = '000000'
