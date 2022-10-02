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
nr_kdamonds_file = os.path.join(kdamonds_dir, 'nr_kdamonds')

def kdamond_dir_of(kdamond_idx):
    return os.path.join(admin_dir, 'kdamonds', '%s' % kdamond_idx)

def state_file_of(kdamond_idx):
    return os.path.join(kdamond_dir_of(kdamond_idx), 'state')

def nr_contexts_file_of(kdamond_idx):
    return os.path.join(kdamond_dir_of(kdamond_idx), 'contexts', 'nr_contexts')

def ctx_dir_of(kdamond_idx, context_idx):
    return os.path.join(kdamond_dir_of(kdamond_idx), 'contexts', '%s' %
            context_idx)

def schemes_dir_of(kdamond_idx, context_idx):
    return os.path.join(ctx_dir_of(kdamond_idx, context_idx), 'schemes')

def nr_schemes_file_of(kdamond_idx, context_idx):
    return os.path.join(schemes_dir_of(kdamond_idx, context_idx), 'nr_schemes')

def targets_dir_of(kdamond_idx, context_idx):
    return os.path.join(ctx_dir_of(kdamond_idx, context_idx), 'targets')

def nr_targets_file_of(kdamond_idx, context_idx):
    return os.path.join(targets_dir_of(kdamond_idx, context_idx), 'nr_targets')

def target_dir_of(kdamond_idx, context_idx, target_idx):
    return os.path.join(ctx_dir_of(kdamond_idx, context_idx), 'targets', '%s' %
            target_idx)

def regions_dir_of(kdamond_idx, context_idx, target_idx):
    return os.path.join(target_dir_of(kdamond_idx, context_idx, target_idx),
            'regions')

def nr_regions_file_of(kdamond_idx, context_idx, target_idx):
    return os.path.join(regions_dir_of(kdamond_idx, context_idx, target_idx),
            'nr_regions')

def __turn_damon(kdamond_idx, on_off):
    err = _damo_fs.write_file(state_file_of(kdamond_idx), on_off)
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

def wops_for_scheme_watermarks(wmarks):
    return {
        'metric': wmarks.metric,
        'interval_us': '%d' % wmarks.interval_us,
        'high': '%d' % wmarks.high_permil,
        'mid': '%d' % wmarks.mid_permil,
        'low': '%d' % wmarks.low_permil,
    }

def wops_for_scheme_quotas(quotas):
    return {
        'ms': '%d' % quotas.time_ms,
        'bytes': '%d' % quotas.sz_bytes,
        'reset_interval_ms': '%d' % quotas.reset_interval_ms,
        'weights': {
            'sz_permil': '%d' % quotas.weight_sz_permil,
            'nr_accesses_permil': '%d' % quotas.weight_nr_accesses_permil,
            'age_permil': '%d' % quotas.weight_age_permil,
        },
    }

def wops_for_scheme_access_pattern(pattern, ctx):
    max_nr_accesses = ctx.intervals.aggr / ctx.intervals.sample

    return {
        'sz': {
            'min': '%d' % pattern.min_sz_bytes,
            'max': '%d' % pattern.max_sz_bytes,
        },
        'nr_accesses': {
            'min': '%d' % int(
                pattern.min_nr_accesses_permil * max_nr_accesses / 1000),
            'max': '%d' % int(
                pattern.max_nr_accesses_permil * max_nr_accesses / 1000),
        },
        'age': {
            'min': '%d' % (pattern.min_age_us / ctx.intervals.aggr),
            'max': '%d' % (pattern.max_age_us / ctx.intervals.aggr),
        },
    }

def wops_for_schemes(ctx):
    schemes = ctx.schemes

    schemes_wops = {}
    for idx, scheme in enumerate(schemes):
        schemes_wops['%d' % idx] = {
            'access_pattern': wops_for_scheme_access_pattern(
                scheme.access_pattern, ctx),
            'action': scheme.action,
            'quotas': wops_for_scheme_quotas(scheme.quotas),
            'watermarks': wops_for_scheme_watermarks(scheme.watermarks),
        }
    return schemes_wops

def wops_for_regions(regions):
    return {'%d' % region_idx: {
        'start': '%d' % region.start,
        'end': '%d' % region.end}
        for region_idx, region in enumerate(regions)}

def wops_for_targets(ctx):
    return {
            '%d' % target_idx: {
                'pid_target': '%s' %
                target.pid if _damon.target_has_pid(ctx.ops) else '',
                'regions': wops_for_regions(target.regions)
                } for target_idx, target in enumerate(ctx.targets)}

def wops_for_monitoring_attrs(ctx):
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

def wops_for_ctx(ctx):
    return [
            {'operations': ctx.ops},
            {'monitoring_attrs': wops_for_monitoring_attrs(ctx)},
            {'targets': wops_for_targets(ctx)},
            {'schemes': wops_for_schemes(ctx)},
    ]

def wops_for_ctxs(ctxs):
    return {'%d' % ctx_idx: wops_for_ctx(ctx) for
            ctx_idx, ctx in enumerate(ctxs)}

def wops_for_kdamond(kdamond):
    return {'contexts': wops_for_ctxs(kdamond.contexts)}

def wops_for_kdamonds(kdamonds):
    return {'%d' % kd_idx: wops_for_kdamond(kdamond) for
            kd_idx, kdamond in enumerate(kdamonds)}

def ensure_dirs_populated_for(kdamonds):
    nr_kdamonds, err = _damo_fs.read_file(nr_kdamonds_file)
    if err != None:
        return err
    if int(nr_kdamonds) != len(kdamonds):
        _damo_fs.write_file_ensure(nr_kdamonds_file, '%d' % len(kdamonds))
    for kd_idx, kdamond in enumerate(kdamonds):
        nr_contexts, err = _damo_fs.read_file(nr_contexts_file_of(kd_idx))
        if err != None:
            return err
        if int(nr_contexts) != len(kdamond.contexts):
            _damo_fs.write_file_ensure(nr_contexts_file_of(kd_idx),
                    '%d' % len(kdamond.contexts))
        for ctx_idx, ctx in enumerate(kdamond.contexts):
            nr_targets, err = _damo_fs.read_file(
                    nr_targets_file_of(kd_idx, ctx_idx))
            if err != None:
                return err
            if int(nr_targets) != len(ctx.targets):
                _damo_fs.write_file_ensure(nr_targets_file_of(kd_idx, ctx_idx),
                        '%d' % len(ctx.targets))
            for target_idx, target in enumerate(ctx.targets):
                nr_regions, err = _damo_fs.read_file(
                        nr_regions_file_of(kd_idx, ctx_idx, target_idx))
                if err != None:
                    return err
                if int(nr_regions) != len(target.regions):
                    _damo_fs.write_file_ensure(
                            nr_regions_file_of(kd_idx, ctx_idx, target_idx),
                            '%d' % len(target.regions))
        nr_schemes, err = _damo_fs.read_file(
                nr_schemes_file_of(kd_idx, ctx_idx))
        if err != None:
            return err
        if int(nr_schemes) != len(ctx.schemes):
            _damo_fs.write_file_ensure(nr_schemes_file_of(kd_idx, ctx_idx),
                    '%d' % len(ctx.schemes))

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
    ensure_dirs_populated_for(kdamonds)

    err = _damo_fs.write_files({kdamonds_dir: wops_for_kdamonds(kdamonds)})
    if err != None:
        print('kdamond applying failed: %s' % err)
        traceback.print_exc()
        return 1

def __commit_inputs(kdamond_idx):
    err = _damo_fs.write_file(state_file_of(kdamond_idx), 'commit')
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

    if not os.path.isdir(ctx_dir_of(0, 0)):
        kdamonds_for_feature_check = [_damon.Kdamond(name=None,
            contexts=[_damon.DamonCtx(intervals=None, nr_regions=None,
                ops=None, targets=[], schemes=[])])]
        ensure_dirs_populated_for(kdamonds_for_feature_check)
    avail_operations_filepath = os.path.join(ctx_dir_of(0, 0),
            'avail_operations')
    if not os.path.isfile(avail_operations_filepath):
        operations_filepath = os.path.join(ctx_dir_of(0, 0), 'operations')
        orig_val, err = _damo_fs.read_file(operations_filepath)
        if err:
            return 'update_supported_features fail (%s)' % err
        for feature in ['vaddr', 'paddr', 'fvaddr', 'vaddr']:
            err = _damo_fs.write_file(operations_filepath, feature)
            if err != None:
                feature_supports[feature] = False
            else:
                feature_supports[feature] = True
        err = _damo_fs.write_file(operations_filepath, orig_val)
        if err:
            return 'update_supported_features fail (%s)' % err
        return None

    content, err = _damo_fs.read_file(avail_operations_filepath)
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
    return None
