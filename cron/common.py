# Copyright (c) 2023, Codecoup.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms and conditions of the GNU General Public License,
# version 2, as published by the Free Software Foundation.
#
# This program is distributed in the hope it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#

"""BTPTester Cron with GitHub CI

Schedule cyclical jobs or trigger them with magic sentence in Pull Request comment.

You can create your own jobs in separate .py file and set them in cron_config.py.

If your ssh private key has password, before running the cron,
start ssh agent in the same console:
$ eval `ssh-agent`
$ ssh-add path/to/id_rsa
"""
import logging
import os
import re
import shlex
import sys
import shutil
import schedule
import requests
import mimetypes
import functools
import traceback
import subprocess
from os import listdir
from pathlib import Path
from time import sleep, time
from os.path import dirname, abspath
from datetime import datetime, date

from common.utils import load_config, check_call, get_global_end
from common.github import update_sources, update_repos
from common.mail import send_mail

BTPTESTER_REPO = os.path.dirname(  # BTPTesterCore repo directory
                    os.path.dirname(  # cron directory
                        os.path.abspath(__file__)))  # this file directory
sys.path.insert(0, BTPTESTER_REPO)

BTPTESTER_STDOUT = 'stdout_btptestercore.log'

log = logging.info
CRON_CFG = {}
mimetypes.add_type('text/plain', '.log')


def set_cron_cfg(cfg):
    global CRON_CFG
    CRON_CFG = cfg


def catch_exceptions(cancel_on_failure=False):
    def _catch_exceptions(job_func):
        @functools.wraps(job_func)
        def __catch_exceptions(*args, **kwargs):
            try:
                return job_func(*args, **kwargs)
            except:
                log(traceback.format_exc())
                print(traceback.format_exc())
                if hasattr(CRON_CFG, 'email'):
                    magic_tag = kwargs['magic_tag'] if 'magic_tag' in kwargs else None
                    send_mail_exception(kwargs['cfg'], CRON_CFG.email, traceback.format_exc(), magic_tag)

                if cancel_on_failure:
                    return schedule.CancelJob
        return __catch_exceptions
    return _catch_exceptions


def format_message(failed, passed, skipped):
    if len(failed) == 0:
        msg = " ✅\n\n"
    else:
        msg = " ❌\n\n"

    msg += "<details><summary>Passed: " + str(len(passed)) + ", Skipped: " + str(len(skipped)) + \
          ", Failed: " + str(len(failed)) + ".</summary>"

    if len(passed) > 0:
        msg += "✅ " + "<br>✅ ".join(passed)
    if len(skipped) > 0:
        msg += "<br>⚠️ " + "<br>⚠️ ".join(skipped)
    if len(failed) > 0:
        msg += "<br>❌ " + "<br>❌ ".join(failed)

    msg += "</details>"

    return msg


def report_to_review_msg(options):
    report_path = os.path.join(BTPTESTER_REPO, BTPTESTER_STDOUT)
    
    failed = []
    passed = []
    skipped = []
    
    msg = '### BTPTester results:'
    devices_role_info = "\n\n#### Central: {}, Peripheral: {}"

    testrun_separator = "------"
    passed_string = '... ok'
    failed_string = '======'
    skipped_string = "... skipped"

    check_twice = False

    central = options[options.index('--central') + 1]
    peripheral = options[options.index('--peripheral') + 1]
    if "--rerun-reverse" in options:
        check_twice = True

    msg += devices_role_info.format(central, peripheral)

    with open(report_path, 'r') as f:
        f.readline()

        # Parsing python's unittest default output
        last_line = ''
        while True:
            line = f.readline()

            if not line:
                if len(failed) == 0 and len(passed) == 0 and len(skipped) == 0:
                    return error_to_review_msg(f)
                break

            if passed_string in line:
                passed.append(last_line.split(' ')[0])
            elif skipped_string in line:
                skipped.append(last_line.split(' ')[0] + ':' + line.split('...')[1])
            elif failed_string in last_line:
                failed.append(line.split(' ')[1])
            elif testrun_separator in line:
                if len(failed) == 0 and len(passed) == 0 and len(skipped) == 0:
                    return error_to_review_msg(f)
                msg += format_message(failed, passed, skipped)
                if check_twice:
                    check_twice = False
                    msg += devices_role_info.format(peripheral, central)
                    failed = []
                    passed = []
                    skipped = []
                    
            last_line = line

    return msg


def error_to_review_msg(report_file):
    msg = '### BTPTesterCore failed:\n'
    report_file.seek(0)
    while True:
        line = report_file.readline()

        if not line:
            break

        msg += line.replace(BTPTESTER_REPO, "BTPTesterCore")

    return msg


def send_mail_exception(conf_name, email_cfg, exception, magic_tag=None):
    iso_cal = date.today().isocalendar()
    ww_dd_str = 'WW%s.%s' % (iso_cal[1], iso_cal[2])

    if magic_tag is not None:
        job_type_info = '<p>Session was triggered with magic sentence: {}</p>'.format(magic_tag)
    else:
        job_type_info = '<p>Session was triggered with cyclical schedule</p>'

    body = '''
    <p>This is automated email and do not reply.</p>
    <h1>Bluetooth test session - {} - FAILED </h1>
    {}
    <p>Config file: {}</p>
    <p>Exception: {}</p>
    <p>Sincerely,</p>
    <p> {}</p>
    '''.format(ww_dd_str, job_type_info, conf_name, exception, email_cfg['name'])

    attachments = []
    if os.path.exists(BTPTESTER_STDOUT):
        attachments.append(BTPTESTER_STDOUT)

    subject = 'BTPTester session FAILED - fail logs'
    send_mail(email_cfg, subject, body, attachments)


def kill_processes(name):
    # Not implemented
    return


def pre_cleanup(btptestercore_repo):
    kill_processes('python.exe')
    pre_cleanup_files(btptestercore_repo)


def pre_cleanup_files(btptestercore_repo):
    files_to_remove = []

    try:
        now = time()
        days_of_validity = 7
        oldlogs_dir = os.path.join(btptestercore_repo, 'oldlogs/')

        for file in listdir(oldlogs_dir):
            file_path = os.path.join(oldlogs_dir, file)
            if os.stat(file_path).st_mtime < now - days_of_validity * 86400:
                files_to_remove.append(file_path)

        for file in files_to_remove:
            file_path = os.path.join(btptestercore_repo, file)
            if os.path.exists(file_path):
                if os.path.isfile(file_path):
                    os.remove(file_path)
                else:
                    shutil.rmtree(file_path, ignore_errors=True)
    except:
        pass


def save_files(btptestercore_repo):
    files_to_save = [
        os.path.join(btptestercore_repo, 'logger_traces.log'),
        os.path.join(btptestercore_repo, 'iut-mynewt-0.log'),
        os.path.join(btptestercore_repo, 'iut-mynewt-1.log'),
        os.path.join(btptestercore_repo, BTPTESTER_STDOUT),
    ]
    try:
        oldlogs_dir = os.path.join(btptestercore_repo, 'oldlogs/')
        save_dir = os.path.join(oldlogs_dir, datetime.now().strftime("%Y_%m_%d_%H_%M"))
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        for file in files_to_save:
            file_path = os.path.join(btptestercore_repo, file)
            if os.path.exists(file_path):
                shutil.move(file_path, os.path.join(save_dir, os.path.basename(file_path)))
    except:
        pass


def git_stash_clear(cwd):
    cmd = 'git stash clear'
    log(f'Running: {cmd}')
    check_call(cmd.split(), cwd=cwd)


def git_checkout(branch, cwd):
    cmd = 'git checkout {}'.format(branch)
    log(f'Running: {cmd}')
    check_call(cmd.split(), cwd=cwd)


def git_rebase_abort(cwd):
    cmd = 'git rebase --abort'
    log(f'Running: {cmd}')
    check_call(cmd.split(), cwd=cwd)


def merge_pr_branch(pr_source_repo_owner, pr_source_branch, repo_name, project_repo):
    cmd = 'git fetch https://github.com/{}/{}.git'.format(
        pr_source_repo_owner, repo_name)
    log(f'Running: {cmd}')
    check_call(cmd.split(), cwd=project_repo)

    cmd = 'git pull --rebase https://github.com/{}/{}.git {}'.format(
        pr_source_repo_owner, repo_name, pr_source_branch)
    log(f'Running: {cmd}')
    check_call(cmd.split(), cwd=project_repo)


def run_test(options, btptestercore_repo):
    # Start subprocess of btptestercore
    cmd = 'python3 btptester.py {}' \
              ' >> {} 2>&1'.format(options, BTPTESTER_STDOUT)
    log(f'Running: {cmd}')
    test_process = subprocess.Popen(cmd,
                                   shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   cwd=btptestercore_repo)

    sleep(5)
    try:
        # Main thread waits for the subprocesses to finish
        while test_process.poll() is None:
            sleep(5)
    except:
        pass

    sleep(10)
    kill_processes('python.exe')

def get_suitable_iuts(cfg, os):
    suitable_iuts = []
    for iut in cfg['iuts']:
        if os in iut['supported_os']:
            suitable_iuts.append(iut)
    if len(suitable_iuts) == 0:
        raise ValueError("No suitable devices found")
    return suitable_iuts

def create_run_options(cfg, os, against=None):
    options = ""

    peripheral_os = os
    if against is not None:
        peripheral_os = against

    suitable_for_pr = get_suitable_iuts(cfg, os)

    # If peripheral device OS is different, run tests twice with role change
    if peripheral_os != os:
        options += '--rerun-reverse'
        suitable_for_peripheral = get_suitable_iuts(cfg, peripheral_os)
        central = suitable_for_pr[0]
        peripheral = suitable_for_peripheral[0]
        if central['serial'] == peripheral['serial']:
            if len(suitable_for_pr) > 1:
                central = suitable_for_pr[1]
            elif len(suitable_for_peripheral) > 1:
                peripheral = suitable_for_peripheral[1]
            else:
                raise ValueError("No suitable devices found")
    else:
        if len(suitable_for_pr) < 2:
            raise ValueError("No suitable devices found")
        central = suitable_for_pr[0]
        peripheral = suitable_for_pr[1]


    options += ' --central {} {} --peripheral {} {}'.format( \
        os, central['serial'], peripheral_os, \
        peripheral['serial'])
    
    for test in cfg['test_options']['tests']:
        options += ' --test {}'.format(test)

    options += ' --flash-central {} {}'.format(central['name'], \
            cfg[os]['project_path'])

    if peripheral_os == os:
        options += ' --flash-peripheral {} {}'.format(peripheral['name'], \
                cfg[os]['project_path'])
    return options


@catch_exceptions(cancel_on_failure=True)
def generic_pr_job(cron, cfg, pr_cfg, pr_repo_name_in_config, **kwargs):
    log('Started PR Job: repo_name={repo_name} PR={number} src_owner={source_repo_owner}'
        ' branch={source_branch} head_sha={head_sha} comment={comment_body} '
        'magic_tag={magic_tag} cfg={cfg}'.format(**pr_cfg, cfg=cfg))

    cfg_dict = load_config(cfg)

    # Path to the project
    PROJECT_REPO = cfg_dict[pr_repo_name_in_config]['project_path']

    # Delete BTPTester logs, tmp files, old bin directories, ...
    pre_cleanup(BTPTESTER_REPO)

    # Update repo.
    cfg_dict[pr_repo_name_in_config]['git'][pr_cfg['repo_name']]['update_repo'] = True
    update_repos(PROJECT_REPO, cfg_dict[pr_repo_name_in_config]['git'])

    # Merge PR branch into local instance of tested repo
    if not os.path.isabs(cfg_dict[pr_repo_name_in_config]['git'][pr_cfg['repo_name']]['path']):
        repo_path = os.path.join(PROJECT_REPO, cfg_dict[pr_repo_name_in_config]['git'][pr_cfg['repo_name']]['path'])
    else:
        repo_path = os.path.abspath(cfg_dict[pr_repo_name_in_config]['git'][pr_cfg['repo_name']]['path'])

    try:
        merge_pr_branch(pr_cfg['source_repo_owner'], pr_cfg['source_branch'],
                        pr_cfg['repo_name'], repo_path)
    except:
        git_rebase_abort(repo_path)
        cron.post_pr_comment(pr_cfg['number'], 'Failed to merge the branch')
        return schedule.CancelJob

    # Create run options
    against = pr_repo_name_in_config
    comment_against = list(filter(lambda x: 'against' in x, pr_cfg['comment_body'].split()))
    if len(comment_against) > 0:
        against = comment_against[0].split('=')[1]
    options = create_run_options(cfg_dict, pr_repo_name_in_config, against)

    # Run BTPTesterCore
    run_test(options, BTPTESTER_REPO)

    git_checkout(cfg_dict[pr_repo_name_in_config]['git'][pr_cfg['repo_name']]['branch'], repo_path)

    # Post in PR comment with results
    cron.post_pr_comment(
        pr_cfg['number'], report_to_review_msg(options.split()))

    save_files(BTPTESTER_REPO)

    log('PR Job finished')

    # To prevent scheduler from cyclical running of the job
    return schedule.CancelJob


@catch_exceptions(cancel_on_failure=True)
def list_available_devices(cron, cfg, pr_cfg, **kwargs):
    cfg_dict = load_config(cfg)
    iuts_dict= {}

    msg = '### BTPTester available devices:\n\n'
    for iut in cfg_dict['iuts']:
        for os in iut['supported_os']:
            if os in iuts_dict:
                iuts_dict[os] += 1
            else:
                iuts_dict[os] = 1
    for iut in iuts_dict:
        msg += iut + ': ' + str(iuts_dict[iut]) + '\n'
    cron.post_pr_comment(pr_cfg['number'], msg)


@catch_exceptions(cancel_on_failure=True)
def generic_test_job(cfg, os, against, **kwargs):
    log(f'Started {cfg} Job')

    cfg_dict = load_config(cfg)

    pre_cleanup(BTPTESTER_REPO)

    print(kwargs)

    options = create_run_options(cfg_dict, os, against)
    run_test(options, BTPTESTER_REPO)

    save_files(BTPTESTER_REPO)

    log(f'{cfg} Job finished')
