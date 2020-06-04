import subprocess
import signal
import os
import sys

if sys.argv[1] == 'fail':
    # kill server process
    p = subprocess.check_output(['ps', '-e', '-f'])
    p = p.decode().splitlines()
    print(p)
    for line  in p:
        if 'coap_main.py' in line:
            pid = int(line.split()[1])
            os.kill(pid, signal.SIGKILL)

    # restart killed server
    path = os.path.dirname(__file__) + '/coap_main.py'
    p = subprocess.Popen(['python3', path], stdout=subprocess.PIPE)
    print('done')

elif sys.argv[1] == 'after-run':
    # kill server process
    p = subprocess.check_output(['ps', '-e', '-f'])
    p = p.decode().splitlines()
    print(p)
    for line in p:
        if 'coap_main.py' in line:
            pid = int(line.split()[1])
            os.kill(pid, signal.SIGKILL)
