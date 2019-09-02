#
# Copyright (c) 2019 JUUL Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

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
