#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON control.
"""

import os
import subprocess

import _damon_dbgfs
import _damon_sysfs
import damon_fs

features = ['record',
            'schemes',
            'init_regions',
            'paddr',
            'init_regions_target_idx',
            'schemes_speed_limit',
            'schemes_quotas',
            'schemes_prioritization',
            'schemes_wmarks',
            ]

_damon_fs = _damon_dbgfs

pr_debug_log = False

def ensure_root_permission():
    if os.geteuid() != 0:
        print('Run as root')
        exit(1)

def set_target(tid, init_regions=[]):
    return _damon_fs.set_target(tid, init_regions)

def turn_damon(on_off):
    return _damon_fs.turn_damon(on_off)

def is_damon_running():
    return _damon_fs.is_damon_running()

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
        return _damon_fs.attrs_apply(self)

def current_attrs():
    return _damon_fs.current_attrs()

def feature_supported(feature):
    return _damon_fs.feature_supported(feature)

def get_supported_features():
    return _damon_fs.get_supported_features()

def initialize(args, skip_dirs_population=False):
    global _damon_fs
    if args.damon_interface == 'sysfs':
        _damon_fs = _damon_sysfs
    elif args.damon_interface == 'debugfs':
        _damon_fs = _damon_dbgfs
    elif args.damon_interface == 'auto':
        err = _damon_sysfs.initialize(args, skip_dirs_population)
        if err == None:
            _damon_fs = _damon_sysfs
        else:
            _damon_fs = _damon_dbgfs

    global pr_debug_log
    if args.debug_damon:
        pr_debug_log = True

    return _damon_fs.initialize(args, skip_dirs_population)

def cmd_args_to_attrs(args):
    'Generate attributes with specified arguments'
    sample_interval = args.sample
    aggr_interval = args.aggr
    regions_update_interval = args.updr
    min_nr_regions = args.minr
    max_nr_regions = args.maxr
    rbuf_len = args.rbuf
    if not os.path.isabs(args.out):
        args.out = os.path.join(os.getcwd(), args.out)
    rfile_path = args.out

    if not hasattr(args, 'schemes'):
        args.schemes = ''
    schemes = args.schemes

    return Attrs(sample_interval, aggr_interval, regions_update_interval,
            min_nr_regions, max_nr_regions, rbuf_len, rfile_path, schemes)

def cmd_args_to_init_regions(args):
    regions = []
    for arg in args.regions.split():
        addrs = arg.split('-')
        try:
            if len(addrs) != 2:
                raise Exception('two addresses not given')
            start = int(addrs[0])
            end = int(addrs[1])
            if start >= end:
                raise Exception('start >= end')
            if regions and regions[-1][1] > start:
                raise Exception('regions overlap')
        except Exception as e:
            print('Wrong \'--regions\' argument (%s)' % e)
            exit(1)

        regions.append([start, end])
    return regions

def read_damon_fs(dir_to_read='/sys/kernel/mm/damon/admin', max_depth=None,
        depth=1):
    if _damon_fs == _damon_dbgfs:
        return damon_fs.read_files('/sys/kernel/debug/damon', max_depth, depth)
    return damon_fs.read_files('/sys/kernel/mm/damon/admin', max_depth, depth)

def write_damon_fs(contents):
    if _damon_fs == _damon_dbgfs:
        damon_fs.write_files('/sys/kernel/debug/damon', contents)
        return
    damon_fs.write_files('/sys/kernel/mm/damon/admin', contents)

def damon_interface():
    if _damon_fs == _damon_sysfs:
        return 'sysfs'
    elif _damon_fs == _damon_dbgfs:
        return 'debugfs'
    print('something wrong')
    raise Exception

def set_common_argparser(parser):
    parser.add_argument('--damon_interface',
            choices=['debugfs', 'sysfs', 'auto'],
            default='auto', help='underlying DAMON interface to use')
    parser.add_argument('--debug_damon', action='store_true',
            help='Print debugging log')
    parser.add_argument('-d', '--debugfs', metavar='<debugfs>', type=str,
            default='/sys/kernel/debug', help='debugfs mounted path')

def set_argparser(parser):
    parser.add_argument('-s', '--sample', metavar='<interval>', type=int,
            default=5000, help='sampling interval (us)')
    parser.add_argument('-a', '--aggr', metavar='<interval>', type=int,
            default=100000, help='aggregate interval (us)')
    parser.add_argument('-u', '--updr', metavar='<interval>', type=int,
            default=1000000, help='regions update interval (us)')
    parser.add_argument('-n', '--minr', metavar='<# regions>', type=int,
            default=10, help='minimal number of regions')
    parser.add_argument('-m', '--maxr', metavar='<# regions>', type=int,
            default=1000, help='maximum number of regions')
    parser.add_argument('-r', '--regions', metavar='"<start>-<end> ..."',
            type=str, default='', help='monitoring target address regions')
    set_common_argparser(parser)
