# TODO: add support for external tools: btmon, serial port output,
#       file management with result sorting
import subprocess
import threading
import serial
import os
import time
import logging
import signal
from queue import Queue
from fcntl import fcntl, F_GETFL, F_SETFL
from os import O_NONBLOCK
from pathlib import Path
import shlex

from coap_config import *

def get_tty_path(name):
    """Returns tty path (eg. /dev/ttyUSB0) of serial device with specified name
    :param name: device name
    :return: tty path if device found, otherwise None
    """
    serial_devices = {}
    ls = subprocess.Popen(["ls", "-l", "/dev/serial/by-id"],
                          stdout=subprocess.PIPE)

    awk = subprocess.Popen("awk '{if (NF > 5) print $(NF-2), $NF}'",
                           stdin=ls.stdout,
                           stdout=subprocess.PIPE,
                           shell=True)

    end_of_pipe = awk.stdout
    for line in end_of_pipe:
        device, serial = line.decode().rstrip().split(" ")
        serial_devices[device] = serial

    for device, serial in list(serial_devices.items()):
        if name in device:
            tty = os.path.basename(serial)
            return "/dev/{}".format(tty)

    return None


class BTMonitor():
    def __init__(self, conn='J-Link', bsp='nrf52', serial_num=None, mode='write', testcase=None):
        self.conn = conn
        self.mode = mode
        self.bsp = bsp
        self.serial_num = serial_num
        self.testcase = testcase
        self.bsp = bsp
        self.process = None
        self.end_read = False

    def read_func_output(self, process, q):
        while not self.end_read:
            output = process.stdout.readline().decode()
            if len(output) > 0:
                logging.debug(output)
                q.put(output)
            if 'RTT opened' in output:
                logging.debug(output)
                break
        return

    def begin(self):
        # stdbuf -o0 removes PIPE buffering: all data on PIPE is ready to be read just when it appears
        cmd = ['stdbuf', '-o0', 'btmon'] + \
              ['-J' if self.conn == 'J-Link' else self.conn] + \
              [str(self.bsp) + ','+ str(self.serial_num) if self.serial_num else str(self.bsp)] + \
              ['-w' if self.mode == 'write' else ''] + \
              [str(self.testcase) + '.snoop' if self.testcase is not None else 'btmonlog.snoop']
        logging.debug(' '.join(cmd))
        self.process = subprocess.Popen(cmd, shell=False, stdout=subprocess.PIPE)

        # Check if process is indeed running
        if self.process.poll() is not None:
            logging.error('Failed to run btmon')
        while True:
            q = Queue()

            thread = threading.Thread(target=self.read_func_output, args=[self.process, q], )
            thread.start()
            thread.join(1)
            if thread.is_alive():
                logging.debug('End btmon output check')
                self.end_read = True
            while True:
                output = q.get()
                logging.debug('queue length: ' + str(q.qsize()))
                logging.debug(output)
                # empty btmon output signals failure on startup; return value can be used to detect it
                if 'RTT opened' in output:
                    logging.debug('btmon connected')
                    return 0
                    # else:
                elif 'Failed to open J-Link' in output:
                    logging.debug('J-Link failed')
                    return 1
                if q.empty():
                    return 1
            return 1

    def close(self):
        os.kill(self.process.pid, signal.SIGINT)
        rc = self.process.wait()
        logging.debug('btmon closed: ' + str(rc))


class RTT2PTY:
    def __init__(self):
        self.rtt2pty_process = None
        self.pty_name = None
        self.serial_thread = None
        self.stop_thread = threading.Event()
        self.log_filename = None
        self.log_file = None
        self.testcase = None

    def _start_rtt2pty_proc(self):
        self.rtt2pty_process = subprocess.Popen('rtt2pty',
                                                shell=False,
                                                stdout=subprocess.PIPE,
                                                stderr=subprocess.PIPE)
        flags = fcntl(self.rtt2pty_process.stdout, F_GETFL) # get current p.stdout flags
        fcntl(self.rtt2pty_process.stdout, F_SETFL, flags | O_NONBLOCK)

        time.sleep(3)
        pty = None
        try:
            for line in iter(self.rtt2pty_process.stdout.readline, b''):
                line = line.decode('UTF-8')
                if line.startswith('PTY name is '):
                    pty = line[len('PTY name is '):].strip()
        except IOError:
            pass

        return pty

    def _read_from_port(self, ser, stop_thread, file):
        current_test = None
        while not stop_thread.is_set():
            if self.testcase != current_test:
                file.write('--- tc: #' + str(self.testcase) + '---\n')
                current_test = self.testcase
            data = ser.read(ser.in_waiting)
            try:
                decoded = data.decode()
            except UnicodeDecodeError:
                continue
            file.write(decoded)
            file.flush()
        return 0

    def start(self, log_filename):
        self.log_filename = log_filename
        self.pty_name = self._start_rtt2pty_proc()

        self.ser = serial.Serial(self.pty_name, 115200, timeout=0)
        self.stop_thread.clear()
        self.log_file = open(self.log_filename, 'a')
        self.serial_thread = threading.Thread(
            target=self._read_from_port, args=(self.ser, self.stop_thread, self.log_file), daemon=True)
        self.serial_thread.start()

    def stop(self):
        self.stop_thread.set()

        if self.serial_thread:
            self.serial_thread.join()
            self.serial_thread = None

        if self.log_file:
            self.log_file.close()
            self.log_file = None

        if self.rtt2pty_process:
            self.rtt2pty_process.send_signal(signal.SIGINT)
            self.rtt2pty_process.wait()
            self.rtt2pty_process = None

    def rtt2pty_start(self):
        if serial_read_enable:
            name = 'iut-mynewt.log'
            self.start(os.path.join(Path.cwd(), name))

    def rtt2pty_stop(self):
        if serial_read_enable:
            self.stop()


class NewtMgr:
    def __init__(self, profile_name: str, conn_type: str, connstring: str, testcase=None):
        self.profile_name = profile_name
        self.conn_type = conn_type
        self.connstring = connstring
        self.testcase = testcase

    def make_profile(self):
        """
        This method adds new connection profile or overwrites the old one, if it exists
        """
        cmd = ['sudo', '-S', 'newtmgr', 'conn', 'add', self.profile_name,
               'type=' + self.conn_type, 'connstring=' + self.connstring]
        process = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output = process.communicate(input=pwd.encode())[0].decode()
        logging.debug(output)
        ctrl = 'Connection profile ' + self.profile_name + ' successfully added'
        if ctrl in output:
            logging.debug('Connection profile \"' + self.profile_name + '\" added')
        else:
            logging.debug('Failed to add connection profile ')

    def check_corefile(self):
        """
        Check if corefile exists; if board is not responding, restart it and check again
        """
        cmd = ['sudo', '-S', 'newtmgr', 'image', 'corelist', '-c', self.profile_name]
        process = subprocess.Popen(cmd, shell=False,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output = process.communicate(input=pwd.encode())[0].decode()
        logging.debug(output)
        # if process executed without errors, determine if corefile is present; print error otherwise
        if output != "":
            if 'Corefile present' in output:
                logging.debug('Board has crashed, corefile present')
                self.download_and_delete_corefile()
            elif 'No corefiles' in output:
                logging.debug('No corefile; system didn\'t crashed or corefile not present')
            else:
                logging.debug('Board crashed; restarting...')
                # restart board
                reset_process = subprocess.Popen(shlex.split(reset_cmd),
                                                 shell=False,
                                                 stdout=subprocess.PIPE,
                                                 stderr=subprocess.PIPE)
                restart_out, _ = reset_process.communicate()
                logging.debug(restart_out)
                time.sleep(3)
                # retry corefile check after restart
                self.check_corefile()

    def download_and_delete_corefile(self):
        logging.debug('Downloading corefile')
        if self.testcase:
            filename = self.testcase + '_coredump'
        else:
            filename = 'default_coredump'
        cmd = ['sudo', 'newtmgr', 'image', 'coredownload', filename, '-c', self.profile_name]
        process = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output = process.communicate(input=pwd.encode())[0].decode()

        if 'Done writing core file' in output:
            cmd = ['sudo', 'newtmgr', 'image', 'coreerase', '-c', self.profile_name]
            process = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            erase_out = process.communicate(input=pwd.encode())[0].decode()
            process.wait()
            logging.debug('Core file erase: ', erase_out)
        else:
            logging.debug('Failed downloading corefile')
