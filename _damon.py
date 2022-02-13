#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON control.
"""

import os
import subprocess

import _damon_dbgfs

features = ['record',
            'schemes',
            'init_regions',
            'paddr',
            'init_regions_target_idx',
            'schemes_speed_limit',
            'schemes_quotas',
            'schemes_prioritization',
            'schemes_wmarks']

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

def set_attrs_argparser(parser):
    parser.add_argument('-d', '--debugfs', metavar='<debugfs>', type=str,
            default='/sys/kernel/debug', help='debugfs mounted path')
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

def set_init_regions_argparser(parser):
    parser.add_argument('-r', '--regions', metavar='"<start>-<end> ..."',
            type=str, default='', help='monitoring target address regions')
