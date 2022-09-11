#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON sysfs control.
"""

import os
import time
import traceback

import _damo_fs
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

def _read(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def turn_damon(on_off):
    if on_off == 'on':
        # In case of vaddr, too early monitoring shows unstable mapping changes.
        # Give the process a time to have stable memory mapping.
        time.sleep(0.5)
    err = _damo_fs.write_files({kdamond_state_file: on_off})
    if err != None:
        print(err)
        return 1
    return 0

def is_damon_running():
    return _read(kdamond_state_file).strip() == 'on'

def ctx_dir_of(kdamond_idx, context_idx):
    return os.path.join(admin_dir, 'kdamonds', '%s' % kdamond_idx,
            'contexts', '%s' % context_idx)

def scheme_dir_of(kdamond_idx, context_idx, scheme_idx):
    return os.path.join(ctx_dir_of(kdamond_idx, context_idx), 'schemes', '%s' %
            scheme_idx)

def __apply_mon_attrs(kdamonds, kdamond_idx, context_idx):
    ctx = kdamonds[kdamond_idx].contexts[context_idx]
    attrs_dir = os.path.join(ctx_dir_of(kdamond_idx, context_idx),
            'monitoring_attrs')

    write_ops = {
            attrs_dir: {
                'intervals': {
                    'sample_us': '%d' % ctx.intervals.sample,
                    'aggr_us': '%d' % ctx.intervals.aggr,
                    'update_us': '%d' % ctx.intervals.ops_update,
                },
                'nr_regions': {
                    'min': '%d' % ctx.nr_regions.min_nr_regions,
                    'max': '%d' % ctx.nr_regions.max_nr_regions,
                },
            }
    }
    err = _damo_fs.write_files(write_ops)
    if err != None:
        print('kdamond applying failed: %s' % err)
        traceback.print_exc()
        return 1
    return 0

def build_scheme_access_pattern_wops(kdamonds, kdamond_idx, context_idx,
        scheme_idx):
    ctx = kdamonds[kdamond_idx].contexts[context_idx]
    scheme = ctx.schemes[scheme_idx]
    access_pattern_dir = os.path.join(scheme_dir_of(kdamond_idx, context_idx,
        scheme_idx), 'access_pattern')

    max_nr_accesses = ctx.intervals.aggr / ctx.intervals.sample
    return {
        access_pattern_dir: {
            'sz': {
                'min': '%d' % scheme.access_pattern.min_sz_bytes,
                'max': '%d' % scheme.access_pattern.max_sz_bytes,
            },
            'nr_accesses': {
                'min': '%d' %
                int(scheme.access_pattern.min_nr_accesses_permil *
                    max_nr_accesses / 1000),
                'max': '%d' %
                int(scheme.access_pattern.max_nr_accesses_permil *
                    max_nr_accesses / 1000),
            },
            'age': {
                'min': '%d' % (scheme.access_pattern.min_age_us /
                    ctx.intervals.aggr),
                'max': '%d' % (scheme.access_pattern.max_age_us /
                    ctx.intervals.aggr),
            }
        }
    }

def build_scheme_quotas_wops(kdamonds, kdamond_idx, context_idx, scheme_idx):
    ctx = kdamonds[kdamond_idx].contexts[context_idx]
    scheme = ctx.schemes[scheme_idx]
    quotas_dir = os.path.join(scheme_dir_of(kdamond_idx, context_idx,
        scheme_idx), 'quotas')

    return {
        quotas_dir: {
            'ms': '%d' % scheme.quotas.time_ms,
            'bytes': '%d' % scheme.quotas.sz_bytes,
            'reset_interval_ms': '%d' % scheme.quotas.reset_interval_ms,
            'weights': {
                'sz_permil': '%d' % scheme.quotas.weight_sz_permil,
                'nr_accesses_permil': '%d' %
                scheme.quotas.weight_nr_accesses_permil,
                'age_permil': '%d' % scheme.quotas.weight_age_permil,
            },
        }
    }

def build_scheme_watermarks_wops(kdamonds, kdamond_idx, context_idx,
        scheme_idx):
    ctx = kdamonds[kdamond_idx].contexts[context_idx]
    scheme = ctx.schemes[scheme_idx]
    wmarks = scheme.watermarks
    wmarks_dir = os.path.join(scheme_dir_of(kdamond_idx, context_idx,
        scheme_idx), 'watermarks')

    return {
        wmarks_dir: {
            'metric': wmarks.metric,
            'interval_us': '%d' % wmarks.interval_us,
            'high': '%d' % wmarks.high_permil,
            'mid': '%d' % wmarks.mid_permil,
            'low': '%d' % wmarks.low_permil,
        }
    }

def __apply_schemes(kdamonds, kdamond_idx, context_idx):
    ctx = kdamonds[kdamond_idx].contexts[context_idx]
    schemes = ctx.schemes
    wops = [{schemes_nr_file: '%d' % len(schemes)}]
    for idx, scheme in enumerate(schemes):
        wops.append(build_scheme_access_pattern_wops(kdamonds, kdamond_idx,
            context_idx, idx))
        wops.append({os.path.join(scheme_dir_of(kdamond_idx, context_idx, idx),
            'action'): scheme.action})
        wops.append(build_scheme_quotas_wops(kdamonds, kdamond_idx,
            context_idx, idx))
        wops.append(build_scheme_watermarks_wops(kdamonds, kdamond_idx,
            context_idx, idx))
    err = _damo_fs.write_files(wops)
    if err:
        print('schemes applying failed: %s' % err)
        traceback.print_exc()
        return 1
    return 0

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
    ret = __apply_mon_attrs(kdamonds, 0, 0)
    if ret != 0:
        return ret

    ret = __apply_schemes(kdamonds, 0, 0)
    if ret != 0:
        return ret

    ctx = kdamonds[0].contexts[0]
    wops = []
    wops.append({context_operations_file: ctx.ops})
    target = ctx.targets[0]
    if _damon.target_has_pid(ctx.ops):
        wops.append({target_pid_file: '%d' % ctx.targets[0].pid})
    wops.append({regions_nr_file: '%d' % len(target.regions)})
    for idx, region in enumerate(target.regions):
        wops.append({region_start_file(idx): '%d' % region.start})
        wops.append({region_end_file(idx): '%d' % region.end})
    err = _damo_fs.write_files(wops)
    if err != None:
        print('kdamond applying failed: %s' % e)
        traceback.print_exc()
        return 1

def commit_inputs():
    err = _damo_fs.write_files({kdamond_state_file: 'commit'})
    if err != None:
        print(err)
        return 1
    return 0

def feature_supported(feature):
    if feature_supports == None:
        update_supported_features()
    return feature_supports[feature]

def dirs_populated():
    return (int(_read(kdamonds_nr_file)) >= 1 and
            int(_read(contexts_nr_file)) >= 1 and
            int(_read(targets_nr_file)) >= 1)

def ensure_dirs_populated():
    if dirs_populated():
        return

    wops = [{kdamonds_nr_file: '1'}]
    wops.append({contexts_nr_file: '1'})
    wops.append({targets_nr_file: '1'})
    err = _damo_fs.write_files(wops)
    if err != None:
        print(err)
        print('failed populating kdamond and context dirs')
        exit(1)

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

    ensure_dirs_populated()
    if not os.path.isfile(context_avail_operations_file):
        for feature in ['vaddr', 'paddr', 'fvaddr', 'vaddr']:
            err = _damo_fs.write_files({context_operations_file: feature})
            if err != None:
                feature_supports[feature] = False
            else:
                feature_supports[feature] = True
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
