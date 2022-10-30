#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON control.
"""

import os
import subprocess
import time

import _damo_fmt_str
import _damo_fs
import _damo_paddr_layout
import _damo_schemes_input
import _damon_dbgfs
import _damon_sysfs

class DamonIntervals:
    sample = None
    aggr = None
    ops_update = None

    def __init__(self, sample, aggr, ops_update):
        self.sample = sample
        self.aggr = aggr
        self.ops_update = ops_update

    def __str__(self):
        return 'sample %s, aggr %s, update %s' % (
                _damo_fmt_str.format_time(self.sample * 1000, False),
                _damo_fmt_str.format_time(self.aggr * 1000, False),
                _damo_fmt_str.format_time(self.ops_update * 1000, False))

    def __eq__(self, other):
        return self.__str__() == other.__str__()

class DamonNrRegionsRange:
    min_nr_regions = None
    max_nr_regions = None

    def __init__(self, min_, max_):
        self.min_nr_regions = min_
        self.max_nr_regions = max_

    def __str__(self):
        return '[%d, %d]' % (self.min_nr_regions, self.max_nr_regions)

    def __eq__(self, other):
        return self.__str__() == other.__str__()

class DamonRegion:
    # [star, end)
    start = None
    end = None

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __str__(self):
        return '[%d, %d) (%s)' % (self.start, self.end,
                _damo_fmt_str.format_sz(self.end - self.start, False))

    def __eq__(self, other):
        return self.__str__() == other.__str__()

class DamonTarget:
    name = None
    pid = None
    regions = None

    def __init__(self, name, pid, regions):
        self.name = name
        self.pid = pid
        self.regions = regions

    def __str__(self):
        lines = ['%s (pid: %s)' % (self.name, self.pid)]
        for region in self.regions:
            lines.append('region %s' % region)
        return '\n'.join(lines)

    def __eq__(self, other):
        return self.__str__() == other.__str__()

class DamosAccessPattern:
    min_sz_bytes = None
    max_sz_bytes = None
    min_nr_accesses = None
    max_nr_accesses = None
    nr_accesses_unit = None # 'percent' or 'sample_intervals'
    min_age = None
    max_age = None
    age_unit = None # 'usec' or 'aggr_intervals'

    def __init__(self, min_sz_bytes, max_sz_bytes,
            min_nr_accesses, max_nr_accesses, nr_accesses_unit,
            min_age, max_age, age_unit):
        self.min_sz_bytes = min_sz_bytes
        self.max_sz_bytes = max_sz_bytes
        self.min_nr_accesses = min_nr_accesses
        self.max_nr_accesses = max_nr_accesses
        self.nr_accesses_unit = nr_accesses_unit
        self.min_age = min_age
        self.max_age = max_age
        self.age_unit = age_unit

    def __str__(self):
        return '\n'.join([
            'sz: [%s, %s]' % (_damo_fmt_str.format_sz(self.min_sz_bytes, False),
                _damo_fmt_str.format_sz(self.max_sz_bytes, False)),
            'nr_accesses: [%d, %d] (%s)' % (
                self.min_nr_accesses, self.max_nr_accesses,
                self.nr_accesses_unit),
            'age: [%d, %d] (%s)' % (self.min_age, self.max_age,
                self.age_unit)])

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.min_sz_bytes ==
                other.min_sz_bytes and self.max_sz_bytes == other.max_sz_bytes
                and self.min_nr_accesses == other.min_nr_accesses and
                self.max_nr_accesses == other.max_nr_accesses and
                self.nr_accesses_unit == other.nr_accesses_unit and
                self.min_age == other.min_age and self.max_age == other.max_age
                and self.age_unit == other.age_unit)

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

    def __str__(self):
        return '\n'.join([
            '%s / %s per %s' % (
                _damo_fmt_str.format_sz(self.time_ms * 1000000, False),
                _damo_fmt_str.format_time(self.sz_bytes, False),
                _damo_fmt_str.format_time(self.reset_interval_ms * 1000000,
                    False)),
            'priority: sz %d permil, nr_accesses %d permil, age %d permil' % (
                self.weight_sz_permil, self.weight_nr_accesses_permil,
                self.weight_age_permil),
            ])

    def __eq__(self, other):
        return (type(self) == type(other) and self.time_ms == other.time_ms and
                self.sz_bytes == other.sz_bytes and self.reset_interval_ms ==
                other.reset_interval_ms and self.weight_sz_permil ==
                other.weight_sz_permil and self.weight_nr_accesses_permil ==
                other.weight_nr_accesses_permil and self.weight_age_permil ==
                other.weight_age_permil)

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

    def __str__(self):
        return '\n'.join([
            '%s/%s/%s permil' % (self.high_permil, self.mid_permil,
                self.low_permil),
            'metric %s, interval %s' % (self.metric,
                _damo_fmt_str.format_time(self.interval_us * 1000, False))
            ])

    def __eq__(self, other):
        return (type(self) == type(other) and self.metric == other.metric and
                self.interval_us == other.interval_us and self.high_permil ==
                other.high_permil and self.mid_permil == other.mid_permil and
                self.low_permil == other.low_permil)

class DamosStats:
    nr_tried = None
    sz_tried = None
    nr_applied = None
    sz_applied = None
    qt_exceeds = None

    def __init__(self, nr_tried, sz_tried, nr_applied, sz_applied, qt_exceeds):
        self.nr_tried = nr_tried
        self.sz_tried = sz_tried
        self.nr_applied = nr_applied
        self.sz_applied = sz_applied
        self.qt_exceeds = qt_exceeds

    def __str__(self):
        return '\n'.join([
            'tried %d times (%s)' % (self.nr_tried,
            _damo_fmt_str.format_sz(self.sz_tried, False)),
            'applied %d times (%s)' % (self.nr_applied,
            _damo_fmt_str.format_sz(self.sz_applied, False)),
            'quota exceeded %d times' % self.qt_exceeds,
            ])

class DamosTriedRegion:
    start = None
    end = None
    nr_accesses = None
    age = None

    def __init__(self, start, end, nr_accesses, age):
        self.start = start
        self.end = end
        self.nr_accesses = nr_accesses
        self.age = age

    def __str__(self):
        return '[%d, %d) (%s): nr_accesses: %d, age: %d' % (self.start,
                self.end, _damo_fmt_str.format_sz(self.end - self.start, False),
                self.nr_accesses, self.age)

class Damos:
    name = None
    access_pattern = None
    action = None
    quotas = None
    watermarks = None
    stats = None
    tried_regions = None

    def __init__(self, name, access_pattern, action, quotas, watermarks,
            stats, tried_regions=None):
        self.name = name
        self.access_pattern = access_pattern
        self.action = action
        self.quotas = quotas
        self.watermarks = watermarks
        self.stats = stats
        self.tried_regions = tried_regions

    def __str__(self):
        lines = ['%s (action: %s)' % (self.name, self.action)]
        lines.append('target access pattern')
        lines.append(_damo_fmt_str.indent_lines('%s' % self.access_pattern, 4))
        lines.append('quotas')
        lines.append(_damo_fmt_str.indent_lines('%s' % self.quotas, 4))
        lines.append('watermarks')
        lines.append(_damo_fmt_str.indent_lines('%s' % self.watermarks, 4))
        lines.append('statistics')
        lines.append(_damo_fmt_str.indent_lines('%s' % self.stats, 4))
        if self.tried_regions != None:
            lines.append('tried regions')
            for region in self.tried_regions:
                lines.append(_damo_fmt_str.indent_lines('%s' % region, 4))
        return '\n'.join(lines)

    def __eq__(self, other):
        return (type(self) == type(other) and self.name == other.name and
                self.access_pattern == other.access_pattern and self.action ==
                other.action and self.quotas == other.quotas and
                self.watermarks == other.watermarks)

class DamonRecord:
    rfile_buf = None
    rfile_path = None

    def __init__(self, rfile_buf, rfile_path):
        self.rfile_buf = rfile_buf
        self.rfile_path = rfile_path

    def __str__(self):
        return 'path: %s, buffer sz: %s' % (self.rfile_path,
                _damo_fmt_str.format_sz(self.rfile_buf))

    def __eq__(self, other):
        return self.__str__() == other.__str__()

class DamonCtx:
    name = None
    intervals = None
    nr_regions = None
    ops = None
    targets = None
    schemes = None
    # For old downstream kernels that supports record feature
    record_request = None

    def __init__(self, name, intervals, nr_regions, ops, targets, schemes):
        self.name = name
        self.intervals = intervals
        self.nr_regions = nr_regions
        self.ops = ops
        self.targets = targets
        self.schemes = schemes

    def __str__(self):
        lines = ['%s (ops: %s)' % (self.name, self.ops)]
        lines.append('intervals: %s' % self.intervals)
        lines.append('nr_regions: %s' % self.nr_regions)
        lines.append('targets')
        for target in self.targets:
            lines.append(_damo_fmt_str.indent_lines('%s' % target, 4))
        lines.append('schemes')
        for scheme in self.schemes:
            lines.append(_damo_fmt_str.indent_lines('%s' % scheme, 4))
        return '\n'.join(lines)

    def __eq__(self, other):
        return self.__str__() == other.__str__()

class Kdamond:
    name = None
    state = None
    pid = None
    contexts = None

    def __init__(self, name, state, pid, contexts):
        self.name = name
        self.state = state
        self.pid = pid
        self.contexts = contexts

    def __str__(self):
        lines = ['%s (state: %s, pid: %s)' % (self.name, self.state, self.pid)]
        for ctx in self.contexts:
            lines.append('contexts')
            lines.append(_damo_fmt_str.indent_lines('%s' % ctx, 4))
        return '\n'.join(lines)

# System check

features = ['record',       # was in DAMON patchset, but not merged in mainline
            'schemes',      # merged in v5.16
            'init_regions', # merged in v5.16 (90bebce9fcd6)
            'vaddr',        # merged in v5.15, thebeginning
            'fvaddr',       # merged in v5.19 (b82434471cd2)
            'paddr',        # merged in v5.16 (a28397beb55b)
            'init_regions_target_idx',  # merged in v5.18 (144760f8e0c3)
            'schemes_speed_limit',      # merged in v5.16 (2b8a248d5873)
            'schemes_quotas',           # merged in v5.16 (1cd243030059)
            'schemes_prioritization',   # merged in v5.16 (38683e003153)
            'schemes_wmarks',           # merged in v5.16 (ee801b7dd782)
            'schemes_stat_succ',        # merged in v5.17 (0e92c2ee9f45)
            'schemes_stat_qt_exceed',   # merged in v5.17 (0e92c2ee9f45)
            'schemes_tried_regions'     # developing on top of v6.0
            ]

_damon_fs = None

pr_debug_log = False

def ensure_root_permission():
    if os.geteuid() != 0:
        print('Run as root')
        exit(1)

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

def damon_interface():
    if _damon_fs == _damon_sysfs:
        return 'sysfs'
    elif _damon_fs == _damon_dbgfs:
        return 'debugfs'
    print('something wrong')
    raise Exception

# DAMON fs read/write

def _damon_fs_root():
    if _damon_fs == _damon_dbgfs:
        return _damon_dbgfs.debugfs_damon
    return _damon_sysfs.admin_dir

def read_damon_fs_from(path):
    return _damo_fs.read_files_recursive(os.path.join(_damon_fs_root(), path))

def read_damon_fs():
    return _damo_fs.read_files_recursive(_damon_fs_root())

def write_damon_fs(contents):
    return _damo_fs.write_files({_damon_fs_root(): contents})

# DAMON status reading

def is_damon_running():
    return _damon_fs.is_damon_running()

def is_kdamond_running(kdamond_name):
    return _damon_fs.is_kdamond_running()

def current_kdamonds():
    return _damon_fs.current_kdamonds()

# DAMON control

def apply_kdamonds(kdamonds):
    _damon_fs.apply_kdamonds(kdamonds)

def commit_inputs(kdamonds):
    if _damon_fs == _damon_dbgfs:
        print('debugfs interface unsupport commit_inputs()')
        exit(1)
    return _damon_fs.commit_inputs(kdamonds)

def update_schemes_stats(kdamond_idx):
    return _damon_fs.update_schemes_stats(kdamond_idx)

def update_schemes_tried_regions(kdamond_idx):
    if _damon_fs == _damon_dbgfs:
        return 'DAMON debugfs doesn\'t support schemes tried regions'
    return _damon_fs.update_schemes_tried_regions(kdamond_idx)

def turn_damon(on_off, kdamonds):
    err = _damon_fs.turn_damon(on_off, kdamonds)
    if err:
        return err
    if on_off == 'on':
        while not is_damon_running():
            time.sleep(1)
    else:   # on_off == 'off'
        while is_damon_running():
            time.sleep(1)

# Kdamonds construction from command line arguments

def target_has_pid(ops):
    return ops in ['vaddr', 'fvaddr']

def damos_from_args(args):
    schemes = []
    if not 'schemes' in args or args.schemes == None:
        return schemes

    return _damo_schemes_input.damo_schemes_to_damos(args.schemes)

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

    target = DamonTarget('0', args.target_pid if target_has_pid(ops) else None,
            init_regions)

    schemes = damos_from_args(args)

    return DamonCtx('0', intervals, nr_regions, ops, [target], schemes)

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

# Command line processing helpers

def is_ongoing_target(args):
    return args.target == 'ongoing'

def apply_explicit_args_damon(args):
    ctx = damon_ctx_from_damon_args(args)
    kdamonds = [Kdamond(name='0', state=None, pid=None, contexts=[ctx])]
    apply_kdamonds(kdamonds)
    return kdamonds

def turn_explicit_args_damon_on(args):
    kdamonds = apply_explicit_args_damon(args)
    return turn_damon('on', kdamonds), kdamonds[0].contexts[0]

def turn_implicit_args_damon_on(args, record_request):
    set_implicit_target_args_explicit(args)
    ctx = damon_ctx_from_damon_args(args)
    if feature_supported('record'):
        ctx.record_request = record_request
    kdamonds = [Kdamond('0', state=None, pid=None, contexts=[ctx])]
    apply_kdamonds(kdamonds)
    return turn_damon('on', kdamonds), kdamonds

# Commandline options setup helpers

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

def set_explicit_target_no_default_schemes_argparser(parser):
    set_explicit_target_monitoring_argparser(parser)
    parser.add_argument('-c', '--schemes', metavar='<file or schemes in text>',
            type=str, help='data access monitoring-based operation schemes')
