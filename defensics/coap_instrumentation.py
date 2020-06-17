import subprocess
import signal
import os
import sys
import shutil
import coap_cfg
from datetime import datetime
from pathlib import Path

if sys.argv[1] == 'fail':
    # kill server process
    p = subprocess.check_output(['ps', '-e', '-f'])
    p = p.decode().splitlines()
    print(p)
    for line in p:
        if 'coap_main.py' in line:
            pid = int(line.split()[1])
            os.kill(pid, signal.SIGKILL)

    # restart killed server
    path = os.path.dirname(__file__) + '/coap_main.py'
    p = subprocess.Popen(['python3', path], stdout=subprocess.PIPE)
    print('Server restarted')
elif sys.argv[1] == 'after-run':
    final_file = coap_cfg.log_filename_final + str(datetime.now()) + '.log'
    print(final_file)
    # kill server process
    p = subprocess.check_output(['ps', '-e', '-f'])
    p = p.decode().splitlines()
    print(p)
    for line in p:
        if 'coap_main.py' in line:
            pid = int(line.split()[1])
            os.kill(pid, signal.SIGKILL)
    # delete temporary logs and create final with timestamp
    shutil.copy(os.path.dirname(__file__) + '/' + coap_cfg.log_filename_temp,
                os.path.dirname(__file__) + '/' + final_file)
    os.remove(os.path.dirname(__file__) + '/' + coap_cfg.log_filename_temp)
