#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON sysfs control.
"""

import os
import time

import _damon

feature_supports = None

# Use only one kdamond, one context, and one target for now
kdamonds_dir = '/sys/kernel/mm/damon/admin/kdamonds'
kdamonds_nr_file = os.path.join(kdamonds_dir, 'nr_kdamonds')
kdamond_dir = os.path.join(kdamonds_dir, '0')
kdamond_state_file = os.path.join(kdamond_dir, 'state')
kdamond_pid_file = os.path.join(kdamond_dir, 'pid')
contexts_dir = os.path.join(kdamond_dir, 'contexts')
contexts_nr_file = os.path.join(contexts_dir, 'nr_contexts')
context_dir = os.path.join(contexts_dir, '0')
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

def set_target(tid, init_regions):
    try:
        if tid == 'paddr':
            _write(context_operations_file, 'paddr')
        else:
            _write(context_operations_file, 'vaddr')
            _write(target_pid_file, '%d' % int(tid))

        _write(regions_nr_file, '%d' % len(init_regions))
        for idx, region in enumerate(init_regions):
            _write(region_start_file(idx), '%d' % region[0])
            _write(region_end_file(idx), '%d' % region[1])
        return 0
    except Exception as e:
        print(e)
        return 1

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

def attrs_apply(attrs):
    if not attrs:
        return 0
    try:
        _write(intervals_sample_us_file, '%d' % attrs.sample_interval)
        _write(intervals_aggr_us_file, '%d' % attrs.aggr_interval)
        _write(intervals_update_us_file, '%d' % attrs.regions_update_interval)
        _write(nr_regions_min_file, '%d' % attrs.min_nr_regions)
        _write(nr_regions_max_file, '%d' % attrs.max_nr_regions)
        schemes = [x for x in attrs.schemes.split('\n') if x != '']
        _write(schemes_nr_file, '%d' % len(schemes))
        # access pattern
        for idx, scheme in enumerate(schemes):
            fields = scheme.split()
            field_idx = 0
            for pattern_dir in ['sz', 'nr_accesses', 'age']:
                for file_ in ['min', 'max']:
                    _write(os.path.join(scheme_dir(idx), 'access_pattern',
                        pattern_dir, file_), fields[field_idx])
                    field_idx += 1
            # action
            dbgfs_action_to_sysfs_action = {
                    0: 'willneed',
                    1: 'cold',
                    2: 'pageout',
                    3: 'hugepage',
                    4: 'nohugepage',
                    5: 'stat',
                    }
            _write(os.path.join(scheme_dir(idx), 'action'),
                    dbgfs_action_to_sysfs_action[int(fields[field_idx])])
            field_idx += 1

            # quotas
            quotas_dir = os.path.join(scheme_dir(idx), 'quotas')
            for file_ in ['ms', 'bytes', 'reset_interval_ms']:
                _write(os.path.join(quotas_dir, file_), fields[field_idx])
                field_idx += 1
            weights_dir = os.path.join(quotas_dir, 'weights')
            for file_ in ['sz_permil', 'nr_accesses_permil', 'age_permil']:
                _write(os.path.join(weights_dir, file_), fields[field_idx])
                field_idx += 1

            # watermarks
            dbgfs_wmark_metroc_to_sysfs_metric = {
                    0: 'none',
                    1: 'free_mem_rate',
                    }
            wmarks_dir = os.path.join(scheme_dir(idx), 'watermarks')
            _write(os.path.join(wmarks_dir, 'metric'),
                    dbgfs_wmark_metroc_to_sysfs_metric[int(fields[field_idx])])
            field_idx += 1
            for file_ in ['interval_us', 'high', 'mid', 'low']:
                _write(os.path.join(wmarks_dir, file_), fields[field_idx])
                field_idx += 1
        return 0
    except Exception as e:
        print(e)
        return 1

# sysfs doesn't restore original state
def current_attrs():
    return None

def feature_supported(feature):
    if feature_supports == None:
        update_supported_features()
    return feature_supports[feature]

def get_supported_features():
    if feature_supports == None:
        update_supported_features()
    return feature_supports

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

def kernel_issue():
    'Return a problem in kernel for using DAMON sysfs interface'
    if not os.path.isdir(kdamonds_dir):
        return 'damon sysfs dir (%s) not found' % kdamonds_dir
    return None

def update_supported_features():
    global feature_supports

    if feature_supports != None:
        return None
    feature_supports = {x: False for x in _damon.features}

    err = kernel_issue()
    if err != None:
        return err
    feature_supports = {x: True for x in _damon.features}
    feature_supports['record'] = False
    return None

def initialize(args=None, skip_dirs_population=False):
    err = update_supported_features()
    if err:
        return err

    if not skip_dirs_population:
        ensure_dirs_populated()
    return None
