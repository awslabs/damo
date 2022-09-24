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
contexts_dir = os.path.join(kdamond_dir, 'contexts')
contexts_nr_file = os.path.join(contexts_dir, 'nr_contexts')
context_dir = os.path.join(contexts_dir, '0')
context_avail_operations_file = os.path.join(context_dir, 'avail_operations')
context_targets_dir = os.path.join(context_dir, 'targets')
targets_nr_file = os.path.join(context_targets_dir, 'nr_targets')

def kdamond_dir_of(kdamond_idx):
    return os.path.join(admin_dir, 'kdamonds', '%s' % kdamond_idx)

def ctx_dir_of(kdamond_idx, context_idx):
    return os.path.join(kdamond_dir_of(kdamond_idx), 'contexts', '%s' %
            context_idx)

def scheme_dir_of(kdamond_idx, context_idx, scheme_idx):
    return os.path.join(ctx_dir_of(kdamond_idx, context_idx), 'schemes', '%s' %
            scheme_idx)

def target_dir_of(kdamond_idx, context_idx, target_idx):
    return os.path.join(ctx_dir_of(kdamond_idx, context_idx), 'targets', '%s' %
            target_idx)

def regions_dir_of(kdamond_idx, context_idx, target_idx):
    return os.path.join(target_dir_of(kdamond_idx, context_idx, target_idx),
            'regions')

def region_dir_of(kdamond_idx, context_idx, target_idx, region_idx):
    return os.path.join(regions_dir_of(kdamond_idx, context_idx, target_idx),
            '%s' % region_idx)

def __turn_damon(kdamond_idx, on_off):
    kdamond_dir = kdamond_dir_of(kdamond_idx)

    write_ops = {
        kdamond_dir: {
            'state': on_off,
            }
    }
    err = _damo_fs.write_files(write_ops)
    if err != None:
        print(err)
        return 1
    return 0

def turn_damon(on_off):
    if on_off == 'on':
        # In case of vaddr, too early monitoring shows unstable mapping changes.
        # Give the process a time to have stable memory mapping.
        time.sleep(0.5)
    return __turn_damon(0, on_off)

def __is_damon_running(kdamond_idx):
    content, err = _damo_fs.read_file(os.path.join(
        kdamond_dir_of(kdamond_idx), 'state'))
    if err != None:
        print(err)
        return False
    return content.strip() == 'on'

def is_damon_running():
    return __is_damon_running(0)

def file_ops_for_monitoring_attrs(ctx):
    return {
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

def file_ops_for_schemes(kdamonds, kdamond_idx, context_idx):
    ctx = kdamonds[kdamond_idx].contexts[context_idx]
    schemes = ctx.schemes
    schemes_dir = os.path.join(ctx_dir_of(kdamond_idx, context_idx), 'schemes')
    wops = [{schemes_dir: {'nr_schemes': '%d' % len(schemes)}}]
    for idx, scheme in enumerate(schemes):
        wops.append(build_scheme_access_pattern_wops(kdamonds, kdamond_idx,
            context_idx, idx))
        wops.append({os.path.join(scheme_dir_of(kdamond_idx, context_idx, idx),
            'action'): scheme.action})
        wops.append(build_scheme_quotas_wops(kdamonds, kdamond_idx,
            context_idx, idx))
        wops.append(build_scheme_watermarks_wops(kdamonds, kdamond_idx,
            context_idx, idx))
    return wops

def apply_kdamonds(kdamonds):
    if len(kdamonds) != 1:
        print('currently only one kdamond is supported')
        exit(1)
    if len(kdamonds[0].contexts) != 1:
        print('currently only one damon_ctx is supported')
        exit(1)
    if len(kdamonds[0].contexts[0].targets) != 1:
        print('currently only one target is supported')
        exit(1)
    ensure_dirs_populated()

    kd_idx = 0  # kdamond index
    ctx_idx = 0
    target_idx = 0

    ctx = kdamonds[kd_idx].contexts[ctx_idx]
    wops = []
    attrs_dir = os.path.join(ctx_dir_of(kd_idx, ctx_idx), 'monitoring_attrs')
    wops.append({attrs_dir: file_ops_for_monitoring_attrs(ctx)})
    wops.append(file_ops_for_schemes(kdamonds, kd_idx, ctx_idx))

    wops.append({ctx_dir_of(kd_idx, ctx_idx): {'operations': ctx.ops}})
    target = ctx.targets[target_idx]
    if _damon.target_has_pid(ctx.ops):
        wops.append({target_dir_of(kd_idx, ctx_idx, target_idx):
            {'pid_target': '%s' % ctx.targets[target_idx].pid}})
    wops.append({regions_dir_of(kd_idx, ctx_idx, target_idx): {
        'nr_regions': '%d' % len(target.regions)}})
    for idx, region in enumerate(target.regions):
        wops.append({region_dir_of(kd_idx, ctx_idx, target_idx, idx): {
            'start': '%d' % region.start,
            'end': '%d' % region.end,
        }})
    err = _damo_fs.write_files(wops)
    if err != None:
        print('kdamond applying failed: %s' % err)
        traceback.print_exc()
        return 1

def __commit_inputs(kdamond_idx):
    err = _damo_fs.write_files(
            {
                kdamond_dir_of(kdamond_idx): {
                    'state': 'commit',
                }
            })
    if err != None:
        print(err)
        return 1
    return 0

def commit_inputs():
    return __commit_inputs(0)

def feature_supported(feature):
    if feature_supports == None:
        update_supported_features()
    return feature_supports[feature]

def dirs_populated():
    files_to_read = {kdamonds_nr_file: None,
            contexts_nr_file: None,
            targets_nr_file: None}
    err = _damo_fs.read_files_of(files_to_read)
    if err:
        print(err)
        return False
    return (int(files_to_read[kdamonds_nr_file]) >= 1 and
            int(files_to_read[contexts_nr_file]) >= 1 and
            int(files_to_read[targets_nr_file]) >= 1)

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
            err = _damo_fs.write_files({ctx_dir_of(0, 0):
                {'operations': feature}})
            if err != None:
                feature_supports[feature] = False
            else:
                feature_supports[feature] = True
        return None

    content, err = _damo_fs.read_file(context_avail_operations_file)
    if err != None:
        print(err)
        return None
    avail_ops = content.strip().split()
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
