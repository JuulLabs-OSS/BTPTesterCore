import subprocess
import logging
import shlex

log = logging.debug

ID = 0


def get_next_id():
    global ID
    next_id = ID
    ID += 1
    return next_id


def nrf_list_devices_cmd():
    return 'nrfjprog -i'


def nrf_reset_cmd(id=None):
    cmd = 'nrfjprog -r'
    if id:
        cmd += ' -s {}'.format(id)

    return cmd


def list_available_boards():
    output = subprocess.check_output(shlex.split(nrf_list_devices_cmd()))
    devices = output.decode().splitlines()
    return devices


class Board:

    nrf52 = "nrf52"

    names = [
        nrf52
    ]

    def __init__(self, board_id, board_name, log_file):
        if board_name not in self.names:
            raise Exception("Board name %s is not supported!" % board_name)

        self.log_file = log_file
        self.board_id = board_id
        self.board_name = board_name

        if self.board_name is self.nrf52:
            self.reset_cmd = nrf_reset_cmd(board_id)

    def reset(self):
        log("About to reset DUT: %r", self.reset_cmd)

        reset_process = subprocess.Popen(shlex.split(self.reset_cmd),
                                         shell=False,
                                         stdout=self.log_file,
                                         stderr=self.log_file)

        if reset_process.wait():
            logging.error("reset failed")
