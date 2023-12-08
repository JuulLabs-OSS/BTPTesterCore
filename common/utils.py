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

import importlib
import os
import subprocess
import sys

from pathlib import Path

PROJECT_DIR = os.path.dirname(  # BTPTesterCore repo directory
                    os.path.dirname(  # common module directory
                        os.path.abspath(__file__)))  # this file directory

GLOBAL_END = False


def check_call(cmd, env=None, cwd=None, shell=True):
    cmd = subprocess.list2cmdline(cmd)
    return subprocess.check_call(cmd, env=env, cwd=cwd, shell=shell)


def get_absolute_module_path(config_path):
    # Path to the config file can be specified as 'config',
    # or 'config.py'.

    _path = os.path.join(PROJECT_DIR, config_path)
    if os.path.isfile(_path):
        return _path

    _path = os.path.join(PROJECT_DIR, f'{config_path}.py')
    if os.path.isfile(_path):
        return _path

    return None


def load_module_from_path(cfg):
    config_path = get_absolute_module_path(cfg)
    if config_path is None:
        log('{} does not exists!'.format(config_path))
        return None

    config_dirname = os.path.dirname(config_path)
    sys.path.insert(0, config_dirname)
    module_name = Path(config_path).stem
    module = importlib.import_module(module_name)
    sys.path.remove(config_dirname)

    return module


def load_config(cfg):
    mod = load_module_from_path(cfg)
    if not mod:
        raise Exception(f'Could not load the config {cfg}')

    return mod.auto_cfg


def set_global_end():
    global GLOBAL_END
    GLOBAL_END = True


def get_global_end():
    return GLOBAL_END
