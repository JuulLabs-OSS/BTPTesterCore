import logging
import threading

from multiprocessing import Process
from queue import Queue, Full
import asyncio
from http.server import HTTPServer
from pathlib import Path
from time import asctime
import shutil
import shlex

from defensics.automation_status import AutomationStatus
from defensics.instrumentation_server import MakeInstrumentationServer
from defensics.tooling import *
from stack.gap import BleAddress
from coap_config import *
from os import devnull
from datetime import datetime
import coap_cfg

from defensics.coap_proxy import CoapProxy, DEVICE_ADDR
from defensics.tcp_server import TCPServer

import dbus
import dbus.mainloop.glib

try:
    from gi.repository import GLib
except ImportError:
    import gobject as GLib

TESTER_ADDR = BleAddress('001bdc069e49', 0)
TESTER_READ_HDL = '0x0003'
TESTER_WRITE_HDL = '0x0005'
TESTER_SERVICE_UUID = '180F'
TESTER_PASSKEY = '000000'

INSTR_STEP_BEFORE_RUN = '/before-run'
INSTR_STEP_BEFORE_CASE = '/before-case'
INSTR_STEP_AS_INSTR = '/as-instrumentation'
INSTR_STEP_AFTER_CASE = '/after-case'
INSTR_STEP_INSTR_FAIL = '/instrument-fail'
INSTR_STEP_AFTER_RUN = '/after-run'

stop_data_handler = False

def handlers_find_starts_with(handlers, key):
    try:
        return next(v for k, v in handlers.items() if key.startswith(k))
    except StopIteration:
        return None


class CoapAutomationHandler(threading.Thread):
    def __init__(self, options):
        super().__init__()
        self.q = Queue()
        self.processing_lock = threading.Lock()
        self.stop_event = threading.Event()  # used to signal termination to the threads
        self.status = AutomationStatus()
        if btmon_enable:
            self.btmon = None
            self.btmon_process = None
            self.max_btmon_tries = 10
        self.result_path = None
        self.test_path = None
        self.newtmgr = None
        self.rtt2pty = None
        self.data_handler_proc = None
        self.options = options

    def _start_data_handel(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        mainloop = GLib.MainLoop()
        tcp = TCPServer('127.0.0.1', 5683)
        proxy = CoapProxy(DEVICE_ADDR, self.options.dev_id)

        automation = DataHandler(proxy, tcp)

        while not automation.is_alive():
            automation.start()
            logging.debug('Automation started')

        mainloop.run()

    def process(self, job):
        global stop_data_handler
        instrumentation_step, params = job
        test_suite = params['CODE_SUITE']
        test_group = params['CODE_TEST_GROUP']
        logging.debug('Test suite {}'.format(test_suite))
        logging.debug('Processing {}'.format(test_group))

        if str.startswith(instrumentation_step, INSTR_STEP_BEFORE_RUN):
            self.processing_lock.acquire()
            logging.debug("Executing: before run")
            logging.debug("Acquire lock")
            # print test run info
            logging.debug('Running suite: ' + params['CODE_SUITE'])
            logging.debug('Platform version: ' + params['CODE_SUITE_PLATFORM_VERSION'])
            logging.debug('Monitor version: ' + params['CODE_MONITOR_VERSION'])
            # make folder for results
            self.result_path = Path.cwd() / asctime()
            self.result_path.mkdir(parents=True, exist_ok=True)
            if crash_detection:
                # make newtmgr instance and add connection
                self.newtmgr = NewtMgr(profile_name='test',
                                       conn_type='oic_serial',
                                       connstring=newtmgr_connstring)
                self.newtmgr.make_profile()
            logging.debug("Release lock")
            # consume buffered serial data by reading it and saving to /dev/null
            if serial_read_enable:
                self.rtt2pty = RTT2PTY()
                self.rtt2pty.rtt2pty_start()
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_BEFORE_CASE):
            self.processing_lock.acquire()
            logging.debug("Executing: before case")
            self.data_handler_proc = Process(target=self._start_data_handel)
            self.data_handler_proc.start()
            # make folder for this test results
            if crash_detection:
                self.newtmgr.testcase = params['CODE_TEST_CASE']
            if serial_read_enable:
                self.rtt2pty.testcase = params['CODE_TEST_CASE']
            if btmon_enable:
                self.test_path = self.result_path / ('#' + params['CODE_TEST_CASE'])
                self.test_path.mkdir(parents=True, exist_ok=True)
            logging.debug("Acquire lock")
            test_case = params['CODE_TEST_CASE']
            # open btmon
            if btmon_enable:
                self.btmon = BTMonitor(testcase=test_case)
                rc = self.btmon.begin()
                logging.debug(rc)
                while rc == 1:
                    logging.debug('restarting btmon')
                    self.btmon.close()
                    self.btmon = BTMonitor(testcase=test_case)

                    rc = self.btmon.begin()
                    logging.debug(rc)
            logging.debug("Release lock")
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_AS_INSTR):
            self.processing_lock.acquire()
            logging.debug("Executing: as instrumentation")
            logging.debug("Acquire lock")
            logging.debug("Release lock")
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_AFTER_CASE):
            self.processing_lock.acquire()
            logging.debug("Executing: after case")
            logging.debug("Acquire lock")
            stop_data_handler = True
            # close btmon
            # copy log files to results folder
            if btmon_enable:
                self.btmon.close()
                self.btmon = None
                snoop_file = Path.cwd() / (params['CODE_TEST_CASE'] + '.snoop')
                shutil.copy(snoop_file, self.test_path)
                Path.unlink(snoop_file)
            logging.debug("Release lock")
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_INSTR_FAIL):
            self.processing_lock.acquire()
            logging.debug("Acquire lock")
            logging.debug("Executing: fail")
            reset_process = subprocess.Popen(shlex.split(reset_cmd),
                                             shell=False,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
            reset_process.wait()
            time.sleep(3)
            self.newtmgr.check_corefile()
            logging.debug("Release lock")
            self.processing_lock.release()
            return

        if str.startswith(instrumentation_step, INSTR_STEP_AFTER_RUN):
            self.processing_lock.acquire()
            logging.debug("Acquire lock")
            logging.debug("Executing: after run")
            if serial_read_enable:
                self.rtt2pty.rtt2pty_stop()
                shutil.move('iut-mynewt.log', self.result_path)
            final_file = coap_cfg.log_filename_final + str(datetime.now()) + '.log'
            # delete temporary logs and create final with timestamp
            final_server_logfile = os.path.dirname(__file__) + '/' + final_file
            shutil.copy(os.path.dirname(__file__) + '/' + coap_cfg.log_filename_temp,
                        final_server_logfile)
            shutil.move(final_server_logfile, self.result_path)

            os.remove(os.path.dirname(__file__) + '/' + coap_cfg.log_filename_temp)
            if crash_detection:
                add_perms_and_move_corefiles(self.result_path)

            # kill server process
            p = subprocess.check_output(['ps', '-e', '-f'])
            p = p.decode().splitlines()
            for line in p:
                if 'coap_main.py' in line:
                    pid = int(line.split()[1])
                    os.kill(pid, signal.SIGKILL)
            logging.debug("Release lock")
            self.processing_lock.release()
            return

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while not self.stop_event.is_set():
            if not self.q.empty():
                item = self.q.get()
                logging.debug('Getting ' + str(item) + ' : ' + str(self.q.qsize()) + ' items in queue')
                try:
                    self.process(item)
                except Exception as e:
                    logging.error('Exception: {}'.format(str(e)))
                    self.status.errors.append(str(e))
                    self.status.verdict = 'fail'
                finally:
                    if self.processing_lock.locked():
                        self.processing_lock.release()
        return

    def post(self, instrumentation_step, params):
        # If we receive next step and we are still processing
        # previous step then we should wait for it to finish
        if self.processing_lock.locked():
            logging.debug('Automation is still processing')

            self.processing_lock.acquire(blocking=True)
            logging.debug('Post release')
            self.processing_lock.release()

        try:
            self.q.put_nowait((instrumentation_step, params))
        except Full:
            self.status.verdict = 'fail'
            self.status.errors.append('Processing queue is full')
            return False

        return True

    def get_status(self):
        s = self.status
        self.status = AutomationStatus()
        return s

    def stop(self):
        self.stop_event.set()

    def parallel(func):
        def parallel_func(*args, **kw):
            p = Process(target=func, args=args, kwargs=kw)
            p.start()

        return parallel_func

    @parallel
    def make_server(self, host, port):
        self.start()
        httpd = HTTPServer((host, port),
                           MakeInstrumentationServer(self))
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            httpd.shutdown()
            return 0


class DataHandler(threading.Thread):
    def __init__(self, proxy: CoapProxy, tcp_server: TCPServer):
        super().__init__()
        self.proxy = proxy
        self.tcp_server = tcp_server
        self.skipping = False
        logging.debug('local proxy: ' + str(self.proxy) + 'global proxy: ' + str(proxy))

    def _run_proxy(self):
        tries = 1
        rc = self.proxy.run()
        while rc != 0 and tries <= 10:
            rc = self.proxy.run()
            logging.debug('Retry starting proxy')
            tries += 1
        logging.debug(str(self.proxy.device_iface) + str(self.proxy.req_char_iface) + str(self.proxy.rsp_char_iface))
        return rc

    def _send_or_pass(self, data):
        if len(data) > 100 and self.skipping:
            return False
        else:
            return True

    def _handle_dbus_exception(self, exception):
        logging.debug(exception.args)
        if 'Did not receive a reply' in exception.args[0]:
            # This error is mostly caused by losing connection with IUT (it crashed or disconnected by itself)
            pass
        elif 'Not connected' in exception.args[0]:
            # if not connected - reconnect. Skip rest of data, as it's continuation of previously
            # sent packets
            self._run_proxy()
        elif 'Operation failed with ATT error:' in exception.args[0]:
            # receiving ATT error means that rest of data is ignored by IUT and can e skipped
            pass
        elif 'Resource Not Ready' in exception.args[0]:
            self._run_proxy()
        elif 'Method "WriteValue" with signature "aya{sv}" on interface "org.bluez.GattCharacteristic1" doesn\'t exist\n':
            self._run_proxy()
        self.skipping = True

    def run(self):
        global stop_data_handler
        self.tcp_server.start()
        logging.debug('running data handler')
        try:
            self._run_proxy()
        except dbus.exceptions.DBusException as ex:
            self._handle_dbus_exception(ex)

        for data in self.tcp_server.recv():
            print(stop_data_handler)
            if self.proxy.is_ready():
                # skipping long data packets, as they're continuation of previously sent long data. Shorter ones
                # might be beginning of new data, so don't ignore them and cancel skip.
                if self._send_or_pass(data):
                    try:
                        rsp = self.proxy.send(data)
                        self.tcp_server.send(rsp)
                    except TimeoutError:
                        # TimeoutError is generated when no response is received, but it isn't expected for every packet
                        pass
                    except dbus.exceptions.DBusException as ex:
                        self._handle_dbus_exception(ex)
            else:
                logging.error('proxy broke, restarting...')
                rc = self._run_proxy()
                if rc != 0:
                    logging.error('could not start proxy, aborting...')
                    return
