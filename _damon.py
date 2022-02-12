#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON control.
"""

import os
import subprocess

import _damon_dbgfs

def chk_permission():
    if os.geteuid() != 0:
        print('Run as root')
        exit(1)

def set_target(tid, init_regions=[]):
    return _damon_dbgfs.set_target(tid, init_regions)

def turn_damon(on_off):
    return _damon_dbgfs.turn_damon(on_off)

def is_damon_running():
    return _damon_dbgfs.is_damon_running()

def current_attrs():
    return _damon_dbgfs.current_attrs()

def feature_supported(feature):
    return _damon_dbgfs.feature_supported(feature)

def get_supported_features():
    return _damon_dbgfs.get_supported_features()

def chk_update_debugfs(debugfs='/sys/kernel/debug/'):
    _damon_dbgfs.chk_update_debugfs(debugfs)

def cmd_args_to_attrs(args):
    return _damon_dbgfs.cmd_args_to_attrs(args)

def cmd_args_to_init_regions(args):
    return _damon_dbgfs.cmd_args_to_attrs(args)

def set_attrs_argparser(parser):
    _damon_dbgfs.set_attrs_argparser(parser)

def set_init_regions_argparser(parser):
    _damon_dbgfs.set_init_regions_argparser(parser)
