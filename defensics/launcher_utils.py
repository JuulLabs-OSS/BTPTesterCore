import os
import subprocess

def selection_cmd(selection_mode, trim_percent):
    cmd = ['--selection-mode', selection_mode]
    if selection_mode == 'trim':
        cmd += ['--trim-percent', trim_percent]
    return cmd


def verbose(debug_info):
    if debug_info:
        return ['--verbose']


def instrumentation_external(script):
    cmd = ['python3', os.path.dirname(os.path.realpath(__file__)) + '/instrumentation_client.py', script]
    return cmd


def after_run():
    cmd = os.path.dirname(os.path.realpath(__file__)) + '/after-run.py'
    return cmd


def indices(index):
    if index == '':
        return ['']
    else:
        cmd = ['--index']
        if isinstance(index, (int, str)):
            cmd.append(str(index))
        elif isinstance(index, list):
            if len(index) > 3 or len(index) < 2:
                raise Exception('Invalid number of parameters in indicies range')
            try:
                cmd.append(', '.join(str(i) for i in range(index[0], index[1], index[2])))
            except IndexError:
                cmd.append(', '.join(str(i) for i in range(index[0], index[1])))
        else:
            raise Exception('Invalid test_indices format')
        return cmd


def defensics_run(cmd):
    while True:
        try:
            cmd.remove('')
        except ValueError:
            break
    print(cmd)
    f = open("def_logs.txt", "w")
    p = subprocess.Popen(cmd, shell=False, stdout=f)
    return p, f


def server_run():
    cmd = ['python3', 'main.py']
    f = open("server_logs.txt", "w")
    p = subprocess.Popen(cmd, shell=False, stdout=f)
    return p, f


def btmon_run(log_file_name):
    cmd = ['btmon', '-J', 'nrf52', '-w', log_file_name + '.log']
    p = subprocess.Popen(cmd, shell=False)
    return p
