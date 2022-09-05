#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON control.
"""

import os
import subprocess

import _convert_damos
import _damo_paddr_layout
import _damon_dbgfs
import _damon_sysfs
import _damo_fs

class DamonIntervals:
    sample = None
    aggr = None
    ops_update = None

    def __init__(self, sample, aggr, ops_update):
        self.sample = sample
        self.aggr = aggr
        self.ops_update = ops_update

class DamonNrRegionsRange:
    min_nr_regions = None
    max_nr_regions = None

    def __init__(self, min_, max_):
        self.min_nr_regions = min_
        self.max_nr_regions = max_

class DamonRegion:
    # [star, end)
    start = None
    end = None

    def __init__(self, start, end):
        self.start = start
        self.end = end

class DamonTarget:
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

class DamonRecord:
    rfile_buf = None
    rfile_path = None

    def __init__(self, rfile_buf, rfile_path):
        self.rfile_buf = rfile_buf
        self.rfile_path = rfile_path

class DamonCtx:
    intervals = None
    nr_regions = None
    ops = None
    targets = None
    schemes = None
    # For old downstream kernels that supports record feature
    record_request = None

    def __init__(self, intervals, nr_regions, ops, targets, schemes):
        self.intervals = intervals
        self.nr_regions = nr_regions
        self.ops = ops
        self.targets = targets
        self.schemes = schemes

class Kdamond:
    name = None
    contexts = None

    def __init__(self, name, contexts):
        self.name = name
        self.contexts = contexts

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

_damon_fs = None

pr_debug_log = False

def ensure_root_permission():
    if os.geteuid() != 0:
        print('Run as root')
        exit(1)

def turn_damon(on_off):
    err = _damon_fs.turn_damon(on_off)
    if err:
        return err
    if on_off == 'on':
        while not is_damon_running():
            time.sleep(1)
    else:   # on_off == 'off'
        while is_damon_running():
            time.sleep(1)

def attrs_to_restore():
    if _damon_fs == _damon_dbgfs:
        return _damon_fs.current_debugfs_inputs()
    else:
        return None

def restore_attrs(attrs):
    if attrs == None:
        return
    if _damon_fs != _damon_dbgfs:
        print('BUG: restore_attrs() called with !None while !debugfs is used')
        return
    _damon_fs.apply_debugfs_inputs(attrs)

def is_damon_running():
    return _damon_fs.is_damon_running()

def apply_kdamonds(kdamonds):
    _damon_fs.apply_kdamonds(kdamonds)

def target_has_pid(ops):
    return ops in ['vaddr', 'fvaddr']

def damos_from_args(args):
    schemes = []
    if not 'schemes' in args:
        return schemes

    scheme_version = _convert_damos.get_scheme_version()

    return _convert_damos.convert(args.schemes, 'damos', args.sample,
            args.aggr, scheme_version)

def damon_ctx_from_damon_args(args):
    intervals = DamonIntervals(args.sample, args.aggr, args.updr)
    nr_regions = DamonNrRegionsRange(args.minr, args.maxr)
    ops = args.ops

    init_regions = []
    if args.regions:
        for region in args.regions.split():
            addrs = region.split('-')
            try:
                if len(addrs) != 2:
                    raise Exception ('two addresses not given')
                region = DamonRegion(int(addrs[0]), int(addrs[1]))
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
        init_regions = [DamonRegion(r[0], r[1]) for r in init_regions]

    if target_has_pid(ops):
        target = DamonTarget(args.target_pid, init_regions)
    else:
        target = DamonTarget(None, init_regions)

    schemes = damos_from_args(args)

    return DamonCtx(intervals, nr_regions, ops, [target], schemes)

def set_implicit_target_args_explicit(args):
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

def feature_supported(feature):
    return _damon_fs.feature_supported(feature)

def initialize(args, skip_dirs_population=False):
    global _damon_fs
    if args.damon_interface == 'sysfs':
        _damon_fs = _damon_sysfs
    elif args.damon_interface == 'debugfs':
        _damon_fs = _damon_dbgfs
    elif args.damon_interface == 'auto':
        err = _damon_sysfs.initialize(skip_dirs_population)
        if err == None:
            _damon_fs = _damon_sysfs
        else:
            _damon_fs = _damon_dbgfs

    global pr_debug_log
    if args.debug_damon:
        pr_debug_log = True

    return _damon_fs.initialize(skip_dirs_population)

initialized = False
def ensure_initialized(args, skip_dirs_population):
    global initialized

    if initialized:
        return
    err = initialize(args, skip_dirs_population)
    if err != None:
        print(err)
        exit(1)
    initialized = True

def commit_inputs():
    if _damon_fs == _damon_dbgfs:
        print('debugfs interface unsupport commit_inputs()')
        exit(1)
    return _damon_fs.commit_inputs()

def _damon_fs_root():
    if _damon_fs == _damon_dbgfs:
        return _damon_dbgfs.debugfs_damon
    return _damon_sysfs.admin_dir

def read_damon_fs():
    return _damo_fs.read_files_recursive(_damon_fs_root())

def write_damon_fs(contents):
    return _damo_fs.write_files({_damon_fs_root(): contents})

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

def set_implicit_target_schemes_argparser(parser):
    set_implicit_target_monitoring_argparser(parser)
    parser.add_argument('-c', '--schemes', metavar='<file or schemes in text>',
            type=str, default='damon.schemes',
            help='data access monitoring-based operation schemes')

def is_ongoing_target(args):
    return args.target == 'ongoing'

def turn_explicit_args_damon_on(args):
    ctx = damon_ctx_from_damon_args(args)
    kdamonds = [Kdamond('0', [ctx])]
    apply_kdamonds(kdamonds)
    return turn_damon('on'), ctx

def turn_implicit_args_damon_on(args, record_request):
    set_implicit_target_args_explicit(args)
    ctx = damon_ctx_from_damon_args(args)
    if feature_supported('record'):
        ctx.record_request = record_request
    kdamonds = [Kdamond('0', [ctx])]
    apply_kdamonds(kdamonds)
    return turn_damon('on'), ctx
