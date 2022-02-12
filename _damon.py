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

class Attrs:
    sample_interval = None
    aggr_interval = None
    regions_update_interval = None
    min_nr_regions = None
    max_nr_regions = None
    rbuf_len = None
    rfile_path = None
    schemes = None

    def __init__(self, s, a, r, n, x, l, f, c):
        self.sample_interval = s
        self.aggr_interval = a
        self.regions_update_interval = r
        self.min_nr_regions = n
        self.max_nr_regions = x
        self.rbuf_len = l
        self.rfile_path = f
        self.schemes = c

    def __str__(self):
        return '%s %s %s %s %s %s %s\n%s' % (self.sample_interval,
                self.aggr_interval, self.regions_update_interval,
                self.min_nr_regions, self.max_nr_regions, self.rbuf_len,
                self.rfile_path, self.schemes)

    def apply(self):
        return _damon_dbgfs.attrs_apply(self)

def current_attrs():
    return _damon_dbgfs.current_attrs()

def feature_supported(feature):
    return _damon_dbgfs.feature_supported(feature)

def get_supported_features():
    return _damon_dbgfs.get_supported_features()

def chk_update(debugfs='/sys/kernel/debug/'):
    _damon_dbgfs.chk_update(debugfs)

def cmd_args_to_attrs(args):
    return _damon_dbgfs.cmd_args_to_attrs(args)

def cmd_args_to_init_regions(args):
    return _damon_dbgfs.cmd_args_to_init_regions(args)

def set_attrs_argparser(parser):
    _damon_dbgfs.set_attrs_argparser(parser)

def set_init_regions_argparser(parser):
    _damon_dbgfs.set_init_regions_argparser(parser)
