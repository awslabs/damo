#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON control.
"""

import os
import subprocess

import _damo_paddr_layout
import _damon_dbgfs
import _damon_sysfs
import damon_fs

features = ['record',
            'schemes',
            'init_regions',
            'vaddr',
            'fvaddr',
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

class Intervals:
    sample = None
    aggr = None
    ops_update = None

    def __init__(self, sample, aggr, ops_update):
        self.sample = sample
        self.aggr = aggr
        self.ops_update = ops_update

class NrRegions:
    min_nr_regions = None
    max_nr_regions = None

    def __init__(self, min_, max_):
        self.min_nr_regions = min_
        self.max_nr_regions = max_

class Region:
    # [star, end)
    start = None
    end = None

    def __init__(self, start, end):
        self.start = start
        self.end = end

class Target:
    pid = None
    regions = None

    def __init__(self, pid, regions):
        self.pid = pid
        self.regions = regions

class DamosAccessPattern:
    min_sz_bytes = None
    max_sz_bytes = None
    min_nr_accesses_permil = None
    max_nr_accesses_permil = None
    min_age_us = None
    max_age_us = None

    def __init__(self, min_sz_bytes, max_sz_bytes, min_nr_accesses_permil,
            max_nr_accesses_permil, min_age_us, max_age_us):
        self.min_sz_bytes = min_sz_bytes
        self.max_sz_bytes = max_sz_bytes
        self.min_nr_accesses_permil = min_nr_accesses_permil
        self.max_nr_accesses_permil = max_nr_accesses_permil
        self.min_age_us = min_age_us
        self.max_age_us = max_age_us

class DamosQuota:
    time_ms = None
    sz_bytes = None
    reset_interval_ms = None
    weight_sz_permil = None
    weight_nr_accesses_permil = None
    weight_age_permil = None

    def __init__(self, time_ms, sz_bytes, reset_interval_ms, weight_sz_permil,
            weight_nr_accesses_permil, weight_age_permil):
        self.time_ms = time_ms
        self.sz_bytes = sz_bytes
        self.reset_interval_ms = reset_interval_ms
        self.weight_sz_permil = weight_sz_permil
        self.weight_nr_accesses_permil = weight_nr_accesses_permil
        self.weight_age_permil = weight_age_permil

class DamosWatermarks:
    metric = None
    interval_us = None
    high_permil = None
    mid_permil = None
    low_permil = None

    def __init__(self, metric, interval_us, high, mid, low):
        self.metric = metric
        self.interval_us = interval_us
        self.high_permil = high
        self.mid_permil = mid
        self.low_permil = low

class Damos:
    access_pattern = None
    action = None
    quotas = None
    watermarks = None

    def __init__(self, access_pattern, action, quotas, watermarks):
        self.access_pattern = access_pattern
        self.action = action
        self.quotas = quotas
        self.watermarks = watermarks

class DamonCtx:
    intervals = None
    nr_regions = None
    ops = None
    targets = None
    schemes = None

    def __init__(self, intervals, nr_regions, ops, targets, schemes):
        self.intervals = intervals
        self.nr_regions = nr_regions
        self.ops = ops
        self.targets = targets
        self.schemes = schemes

    def set_intervals(self, sample, aggr, ops_update):
        self.intervals = Intervals(sample, aggr, ops_update)

    def set_nr_regions(self, min_, max_):
        self.nr_regions = NrRegions(min_, max_)

    def set_ops(self, ops):
        self.ops = ops

    def set_targets(targets):
        self.targets = targets

class Kdamond:
    name = None
    contexts = None

    def __init__(self, name, contexts):
        self.name = name
        self.contexts = contexts

    def on(self):
        _damon_fs.turn_kdamond_on(self)

    def off(self):
        _damon_fs.turn_kdamond_off(self)

    def commit(self):
        _damon_fs.commit_kdamond(self)

    # TODO: Implement
    def update_schemes_stats(self):
        pass

def apply_kdamonds(kdamonds):
    _damon_fs.apply_kdamonds(kdamonds)

def target_has_pid(ops):
    return ops in ['vaddr', 'fvaddr']

def damon_ctx_from_damon_args(args):
    intervals = Intervals(args.sample, args.aggr, args.updr)
    nr_regions = NrRegions(args.minr, args.maxr)
    ops = args.ops

    init_regions = []
    if args.regions:
        for region in args.regions.split():
            addrs = region.split('-')
            try:
                if len(addrs) != 2:
                    raise Exception ('two addresses not given')
                region = Region(int(addrs[0]), int(addrs[1]))
                if region.start >= region.end:
                    raise Exception('start >= end')
                if init_regions and init_regions[-1].end > region.start:
                    raise Exception('regions overlap')
            except Exception as e:
                print('Wrong \'--regions\' argument (%s)' % e)
                exit(1)
            init_regions.append(region)

    if ops == 'paddr' and not init_regions:
        if args.numa_node != None:
            init_regions = _damo_paddr_layout.paddr_region_of(args.numa_node)
        else:
            init_regions = [_damo_paddr_layout.default_paddr_region()]
        init_regions = [Region(r[0], r[1]) for r in init_regions]

    if target_has_pid(ops):
        target = Target(args.target_pid, init_regions)
    else:
        target = Target(None, init_regions)
    return DamonCtx(intervals, nr_regions, ops, [target], [])

def implicit_target_args_to_explicit_target_args(args):
    args.self_started_target = False
    if args.target == 'paddr':
        args.ops = 'paddr'
        args.target_pid = None
        return
    if not subprocess.call('which %s &> /dev/null' % args.target.split()[0],
            shell=True, executable='/bin/bash'):
        p = subprocess.Popen(args.target, shell=True, executable='/bin/bash')
        args.ops = 'vaddr'
        args.target_pid = p.pid
        args.self_started_target = True
        if args.regions and feature_supported('fvaddr'):
            args.ops = 'fvaddr'
        return
    try:
        pid = int(args.target)
    except:
        print('target \'%s\' is not supported' % args.target)
        exit(1)
    args.ops = 'vaddr'
    args.target_pid = pid
    if args.regions and feature_supported('fvaddr'):
        args.ops = 'fvaddr'

    return

# =============
# Old interface
# =============

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

def commit_inputs():
    if _damon_fs == _damon_dbgfs:
        print('debugfs interface unsupport commit_inputs()')
        exit(1)
    return _damon_fs.commit_inputs()

def read_damon_fs(max_depth=None, depth=1):
    if _damon_fs == _damon_dbgfs:
        return damon_fs.read_files(_damon_dbgfs.debugfs_damon, max_depth,
                depth)
    return damon_fs.read_files(_damon_sysfs.admin_dir, max_depth, depth)

def write_damon_fs(contents):
    if _damon_fs == _damon_dbgfs:
        damon_fs.write_files(_damon_dbgfs.debugfs_damon, contents)
        return
    damon_fs.write_files(_damon_sysfs.admin_dir, contents)

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

def set_common_monitoring_argparser(parser):
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
    parser.add_argument('--numa_node', metavar='<node id>', type=int,
            help='if target is \'paddr\', limit it to the numa node')

def set_implicit_target_monitoring_argparser(parser):
    set_common_monitoring_argparser(parser)
    parser.add_argument('target', type=str, metavar='<target>',
            help='the target (command, pid, or special keywords) to monitor')
    set_common_argparser(parser)

def set_explicit_target_monitoring_argparser(parser):
    set_common_monitoring_argparser(parser)
    parser.add_argument('ops', choices=['vaddr', 'paddr', 'fvaddr'],
            default='vaddr',
            help='monitoring operations set')
    parser.add_argument('--target_pid', type=int, help='target pid')
    set_common_argparser(parser)

