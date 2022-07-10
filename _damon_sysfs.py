#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON sysfs control.
"""

import os
import time
import traceback

import _damon

feature_supports = None

# Use only one kdamond, one context, and one target for now
root_dir = '/sys/kernel/mm/damon'
admin_dir = os.path.join(root_dir, 'admin')
kdamonds_dir = os.path.join(admin_dir, 'kdamonds')
kdamonds_nr_file = os.path.join(kdamonds_dir, 'nr_kdamonds')
kdamond_dir = os.path.join(kdamonds_dir, '0')
kdamond_state_file = os.path.join(kdamond_dir, 'state')
kdamond_pid_file = os.path.join(kdamond_dir, 'pid')
contexts_dir = os.path.join(kdamond_dir, 'contexts')
contexts_nr_file = os.path.join(contexts_dir, 'nr_contexts')
context_dir = os.path.join(contexts_dir, '0')
context_avail_operations_file = os.path.join(context_dir, 'avail_operations')
context_operations_file = os.path.join(context_dir, 'operations')
context_attrs_dir = os.path.join(context_dir, 'monitoring_attrs')
attrs_intervals_dir = os.path.join(context_attrs_dir, 'intervals')
intervals_sample_us_file = os.path.join(attrs_intervals_dir, 'sample_us')
intervals_aggr_us_file = os.path.join(attrs_intervals_dir, 'aggr_us')
intervals_update_us_file = os.path.join(attrs_intervals_dir, 'update_us')
attrs_nr_regions_dir = os.path.join(context_attrs_dir, 'nr_regions')
nr_regions_min_file = os.path.join(attrs_nr_regions_dir, 'min')
nr_regions_max_file = os.path.join(attrs_nr_regions_dir, 'max')
context_targets_dir = os.path.join(context_dir, 'targets')
targets_nr_file = os.path.join(context_targets_dir, 'nr_targets')
target_dir = os.path.join(context_targets_dir, '0')
target_pid_file = os.path.join(target_dir, 'pid_target')
target_regions_dir = os.path.join(target_dir, 'regions')
regions_nr_file = os.path.join(target_regions_dir, 'nr_regions')

def region_dir(region_idx):
    return os.path.join(target_regions_dir, '%d' % region_idx)

def region_start_file(region_idx):
    return os.path.join(region_dir(region_idx), 'start')

def region_end_file(region_idx):
    return os.path.join(region_dir(region_idx), 'end')

schemes_dir = os.path.join(context_dir, 'schemes')
schemes_nr_file = os.path.join(schemes_dir, 'nr_schemes')

def scheme_dir(scheme_idx):
    return os.path.join(schemes_dir, '%d' % scheme_idx)

# This class will be used in a future when we support multiple
# contexts/kdamonds
class DamonSysfsFile:
    indices = None  # e.g., {'kdamond': 0, 'context': 1}
    extra_path = None

    def __init__(self, indices, extra_path=None):
        self.indices = indices
        self.extra_path = extra_path

    def path(self):
        path = kdamonds_dir
        for keyword in ['kdamond', 'context', 'scheme', 'target',
                'region']:
            if keyword in self.indices:
                path = os.path.join(path, keyword + 's', self.indices[keyword])
        if self.extra_path:
            path = os.path.join(path, self.extra_path)
        return path

    def __str__(self):
        return self.path()

    def __repr__(self):
        return self.path()

    def regions_dir(self):
        return DamonSysfsFile(file_idx='regions',
                kdamond_idx=self.kdamond_idx, context_idx=self.context_idx,
                target_idx=self.target_idx)

    def regions_nr(self):
        return DamonSysfsFile(file_idx='regions/nr',
                kdamond_idx=self.kdamond_idx, context_idx=self.context_idx,
                target_idx=self.target_idx)

    def write(self, content):
        with open(self.path(), 'w') as f:
            f.write(content)

def _write(filepath, content):
    if _damon.pr_debug_log:
        print('write %s to %s' % (content, filepath))
    with open(filepath, 'w') as f:
        f.write(content)

def _read(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def turn_damon(on_off):
    if on_off == 'on':
        # In case of vaddr, too early monitoring shows unstable mapping changes.
        # Give the process a time to have stable memory mapping.
        time.sleep(0.5)
    try:
        _write(kdamond_state_file, on_off)
        return 0
    except Exception as e:
        print(e)
        return 1

def is_damon_running():
    return _read(kdamond_state_file).strip() == 'on'

def apply_kdamonds(kdamonds):
    if len(kdamonds) != 1:
        print('Currently only one kdamond is supported')
        exit(1)
    if len(kdamonds[0].contexts) != 1:
        print('currently only one damon_ctx is supported')
        exit(1)
    if len(kdamonds[0].contexts[0].targets) != 1:
        print('currently only one target is supported')
        exit(1)
    ensure_dirs_populated()
    ctx = kdamonds[0].contexts[0]
    try:
        _write(intervals_sample_us_file, '%d' % ctx.intervals.sample)
        _write(intervals_aggr_us_file, '%d' % ctx.intervals.aggr)
        _write(intervals_update_us_file, '%d' % ctx.intervals.ops_update)
        _write(nr_regions_min_file, '%d' % ctx.nr_regions.min_nr_regions)
        _write(nr_regions_max_file, '%d' % ctx.nr_regions.max_nr_regions)

        schemes = ctx.schemes
        _write(schemes_nr_file, '%d' % len(schemes))
        for idx, scheme in enumerate(schemes):
            # access pattern
            max_nr_accesses = ctx.intervals.aggr / ctx.intervals.sample
            _write(os.path.join(scheme_dir(idx), 'access_pattern', 'sz',
                'min'), '%d' % scheme.access_pattern.min_sz_bytes)
            _write(os.path.join(scheme_dir(idx), 'access_pattern', 'sz',
                'max'), '%d' % scheme.access_pattern.max_sz_bytes)
            _write(os.path.join(scheme_dir(idx), 'access_pattern',
                'nr_accesses', 'min'),
                '%d' % int(scheme.access_pattern.min_nr_accesses_permil *
                    max_nr_accesses / 1000))
            _write(os.path.join(scheme_dir(idx), 'access_pattern',
                'nr_accesses', 'max'),
                '%d' % int(scheme.access_pattern.max_nr_accesses_permil *
                    max_nr_accesses / 1000))
            _write(os.path.join(scheme_dir(idx), 'access_pattern',
                'age', 'min'), '%d' % (scheme.access_pattern.min_age_us /
                ctx.intervals.aggr))
            _write(os.path.join(scheme_dir(idx), 'access_pattern',
                'age', 'max'), '%d' % (scheme.access_pattern.max_age_us /
                ctx.intervals.aggr))

            _write(os.path.join(scheme_dir(idx), 'action'), scheme.action)

            # quotas
            quotas_dir = os.path.join(scheme_dir(idx), 'quotas')
            _write(os.path.join(quotas_dir, 'ms'), '%d' %
                    scheme.quotas.time_ms)
            _write(os.path.join(quotas_dir, 'bytes'), '%d' %
                    scheme.quotas.sz_bytes)
            _write(os.path.join(quotas_dir, 'reset_interval_ms'), '%d' %
                    scheme.quotas.reset_interval_ms)
            weights_dir = os.path.join(quotas_dir, 'weights')
            _write(os.path.join(weights_dir, 'sz_permil'), '%d' %
                    scheme.quotas.weight_sz_permil)
            _write(os.path.join(weights_dir, 'nr_accesses_permil'), '%d' %
                    scheme.quotas.weight_nr_accesses_permil)
            _write(os.path.join(weights_dir, 'age_permil'), '%d' %
                    scheme.quotas.weight_age_permil)

            # watermarks
            wmarks = scheme.watermarks
            wmarks_dir = os.path.join(scheme_dir(idx), 'watermarks')
            _write(os.path.join(wmarks_dir, 'metric'), wmarks.metric)
            _write(os.path.join(wmarks_dir, 'interval_us'), '%d' %
                    wmarks.interval_us)
            _write(os.path.join(wmarks_dir, 'high'), '%d' % wmarks.high_permil)
            _write(os.path.join(wmarks_dir, 'mid'), '%d' % wmarks.mid_permil)
            _write(os.path.join(wmarks_dir, 'low'), '%d' % wmarks.low_permil)

        _write(context_operations_file, ctx.ops)

        target = ctx.targets[0]
        if _damon.target_has_pid(ctx.ops):
            _write(target_pid_file, '%d' % ctx.targets[0].pid)
        _write(regions_nr_file, '%d' % len(target.regions))
        for idx, region in enumerate(target.regions):
            _write(region_start_file(idx), '%d' % region.start)
            _write(region_end_file(idx), '%d' % region.end)
    except Exception as e:
        print('kdamond applying failed: %s' % e)
        traceback.print_exc()
        return 1

def commit_inputs():
    try:
        _write(kdamond_state_file, 'commit')
        return 0
    except Exception as e:
        print(e)
        return 1

def feature_supported(feature):
    if feature_supports == None:
        update_supported_features()
    return feature_supports[feature]

populated = False
def ensure_dirs_populated():
    global populated
    if populated:
        return

    try:
        _write(kdamonds_nr_file, '1')
        _write(contexts_nr_file, '1')
        _write(targets_nr_file, '1')
        populated = True
    except Exception as e:
        print(e)
        print('failed populating kdamond and context dirs')
        exit(1)

def dirs_populated():
    return (int(_read(kdamonds_nr_file)) >= 1 and
            int(_read(contexts_nr_file)) >= 1 and
            int(_read(targets_nr_file)) >= 1)

def damon_sysfs_missed():
    'Return none-None if DAMON sysfs interface is not found'
    if not os.path.isdir(kdamonds_dir):
        return 'damon sysfs dir (%s) not found' % kdamonds_dir
    return None

def update_supported_features():
    global feature_supports

    if feature_supports != None:
        return None
    feature_supports = {x: False for x in _damon.features}

    missed = damon_sysfs_missed()
    if missed != None:
        return missed
    feature_supports = {x: True for x in _damon.features}
    feature_supports['record'] = False

    if not dirs_populated():
        ensure_dirs_populated()
    if not os.path.isfile(context_avail_operations_file):
        for feature in ['vaddr', 'paddr', 'fvaddr', 'vaddr']:
            try:
                _write(context_operations_file, feature)
                feature_supports[feature] = True
            except IOError:
                feature_supports[feature] = False
        return None

    avail_ops = _read(context_avail_operations_file).strip().split()
    for feature in ['vaddr', 'paddr', 'fvaddr']:
        feature_supports[feature] = feature in avail_ops

    return None

def initialize(skip_dirs_population=False):
    err = update_supported_features()
    if err:
        return err

    if not skip_dirs_population:
        ensure_dirs_populated()
    return None
