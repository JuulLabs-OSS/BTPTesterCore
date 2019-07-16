import atexit
import shlex
import subprocess
import time

SYMLINK_NAME = 'btptester'


class RTT2PTY:
    def __init__(self, board_id, buffer_name):
        self.board_id = board_id
        self.buffer_name = buffer_name
        self.proc = None
        self.pty_file = "{}-{}".format(SYMLINK_NAME, self.board_id)
        self.cmd = "rtt2pty -2 -b {} -l {} -s {}".format(self.buffer_name,
                                                         self.pty_file,
                                                         self.board_id)

        atexit.register(self.cleanup)

    def get_pty_file(self):
        return self.pty_file

    def start(self):
        if self.proc:
            raise Exception("RTT2PTY process already started")

        print("Executing command: {}".format(self.cmd))
        time.sleep(3)
        self.proc = subprocess.Popen(shlex.split(self.cmd))

    def is_running(self):
        return self.proc.poll() is None

    def cleanup(self):
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            self.proc.wait()
