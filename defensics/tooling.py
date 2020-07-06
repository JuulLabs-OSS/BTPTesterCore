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

from coap_config import *


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


class SerialOutput(threading.Thread):
    def __init__(self, testcase=None, port='/dev/ttyACM0', bauderate=115200,
                 path=os.getcwd(), newtmgr=None):
        self.connection = serial.Serial(port=port, baudrate=bauderate, timeout=None)
        self.testcase = testcase
        self.path = path
        self.process = None
        self.shutdown = False
        self.newtmgr = newtmgr

        super(SerialOutput, self).__init__()

    def run(self):
        logging.debug('Capturing console output')
        if self.testcase:
            filename = str(self.testcase) + '.txt'
        else:
            filename = 'test.txt'
        file = open(filename, 'a')
        while not self.shutdown:
            # limit data acquisition frequency
            time.sleep(1)
            bytesToRead = self.connection.inWaiting()
            data = self.connection.read(bytesToRead).decode('utf-8')
            if crash_detection:
                if 'Unhandled interrupt' in data:
                    self.newtmgr.check_corefile()
            file.write(data)
            file.flush()
        # before ending wait half a second for data to appear; save what arrived
        time.sleep(1)
        bytesToRead = self.connection.inWaiting()
        data = self.connection.readline(bytesToRead).decode()
        logging.debug('Saving console output file')
        file.write(data)
        file.close()


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
            logging.debug('Connection profile added')
        else:
            logging.debug('Failed to add connection profile ')

    def check_corefile(self):
        """
        Check if corefile exists; if board is not responding, restart it and check again
        """
        cmd = ['sudo', '-S', 'newtmgr', 'image', 'corelist', '-c', self.profile_name]
        process = subprocess.Popen(cmd, shell=False,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = process.communicate(input=pwd.encode())[0].decode()
        logging.debug(output)
        # if process executed without errors, determine if corefile is present; print error otherwise
        if output[1] == "":
            if 'Corefile present' in output:
                logging.debug('Board has crashed, corefile present')
                self.download_and_delete_corefile()
            elif 'No corefiles' in output:
                logging.debug('No corefile; system didn\'t crashed or corefile not present')
            else:
                logging.debug('Board crashed; restarting...')
                # restart board
                restart = subprocess.check_output(['nrfjprog', '-r']).decode()
                logging.debug(restart)
                # retry corefile check after restart
                self.check_corefile()
        else:
            logging.error(output[1].decode())

    def download_and_delete_corefile(self):
        if self.testcase:
            filename = self.testcase + '.coredump'
        else:
            filename = 'default.coredump'
        cmd = ['sudo', 'newtmgr', 'image', 'coredownload', filename, '-c', self.profile_name]
        process = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output = process.communicate(input=pwd.encode())[0].decode()
        if 'Done writing core file' in output:
            cmd = ['sudo', 'newtmgr', 'image', 'coreerase', '-c', self.profile_name]
            process = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            process.communicate(input=pwd.encode())[0].decode()
            return 0
        else:
            logging.debug('Failed downloading corefile')
            return 1
