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
import _damon_result

feature_supports = None

# Use only one kdamond, one context, and one target for now
root_dir = '/sys/kernel/mm/damon'
admin_dir = os.path.join(root_dir, 'admin')
kdamonds_dir = os.path.join(admin_dir, 'kdamonds')
nr_kdamonds_file = os.path.join(kdamonds_dir, 'nr_kdamonds')

def kdamond_dir_of(kdamond_name):
    return os.path.join(admin_dir, 'kdamonds', '%s' % kdamond_name)

def state_file_of(kdamond_name):
    return os.path.join(kdamond_dir_of(kdamond_name), 'state')

def nr_contexts_file_of(kdamond_name):
    return os.path.join(
            kdamond_dir_of(kdamond_name), 'contexts', 'nr_contexts')

def ctx_dir_of(kdamond_name, context_name):
    return os.path.join(
            kdamond_dir_of(kdamond_name), 'contexts', '%s' % context_name)

def schemes_dir_of(kdamond_name, context_name):
    return os.path.join(ctx_dir_of(kdamond_name, context_name), 'schemes')

def nr_schemes_file_of(kdamond_name, context_name):
    return os.path.join(
            schemes_dir_of(kdamond_name, context_name), 'nr_schemes')

def scheme_dir_of(kdamond_name, context_name, scheme_name):
    return os.path.join(
            schemes_dir_of(kdamond_name, context_name), '%s' % scheme_name)

def targets_dir_of(kdamond_name, context_name):
    return os.path.join(ctx_dir_of(kdamond_name, context_name), 'targets')

def nr_targets_file_of(kdamond_name, context_name):
    return os.path.join(
            targets_dir_of(kdamond_name, context_name), 'nr_targets')

def target_dir_of(kdamond_name, context_name, target_name):
    return os.path.join(ctx_dir_of(kdamond_name, context_name), 'targets',
            '%s' % target_name)

def regions_dir_of(kdamond_name, context_name, target_name):
    return os.path.join(
            target_dir_of(kdamond_name, context_name, target_name), 'regions')

def nr_regions_file_of(kdamond_name, context_name, target_name):
    return os.path.join(
            regions_dir_of(kdamond_name, context_name, target_name),
            'nr_regions')

def supported():
    return os.path.isdir(kdamonds_dir)

def turn_damon(on_off, kdamonds_names):
    if on_off == 'on':
        # In case of vaddr, too early monitoring shows unstable mapping changes.
        # Give the process a time to have stable memory mapping.
        time.sleep(0.5)
    for kdamond_name in kdamonds_names:
        err = _damo_fs.write_file(state_file_of(kdamond_name), on_off)
        if err != None:
            print(err)
            return 1
    return 0

def is_kdamond_running(kdamond_name):
    content, err = _damo_fs.read_file(state_file_of(kdamond_name))
    if err != None:
        print(err)
        return False
    return content.strip() == 'on'

'Return error'
def update_schemes_stats(kdamond_name):
    return _damo_fs.write_files({state_file_of(kdamond_name):
        'update_schemes_stats'})

'Return error'
def update_schemes_tried_regions(kdamond_name):
    return _damo_fs.write_files({state_file_of(kdamond_name):
        'update_schemes_tried_regions'})

# for apply_kdamonds

def wops_for_scheme_watermarks(wmarks):
    if wmarks == None:
        return {}
    return {
        'metric': wmarks.metric,
        'interval_us': '%d' % wmarks.interval_us,
        'high': '%d' % wmarks.high_permil,
        'mid': '%d' % wmarks.mid_permil,
        'low': '%d' % wmarks.low_permil,
    }

def wops_for_scheme_quotas(quotas):
    if quotas == None:
        return {}
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
    if pattern == None:
        return {}
    max_nr_accesses = ctx.intervals.aggr / ctx.intervals.sample

    return {
        'sz': {
            'min': '%d' % pattern.min_sz_bytes,
            'max': '%d' % pattern.max_sz_bytes,
        },
        'nr_accesses': {
            'min': '%d' % int(
                pattern.min_nr_accesses * max_nr_accesses / 100
                if pattern.nr_accesses_unit == 'percent'
                else pattern.min_nr_accesses),
            'max': '%d' % int(
                pattern.max_nr_accesses * max_nr_accesses / 100
                if pattern.nr_accesses_unit == 'percent'
                else pattern.max_nr_accesses),
        },
        'age': {
            'min': '%d' % (pattern.min_age / ctx.intervals.aggr
                if pattern.age_unit == 'usec' else pattern.min_age),
            'max': '%d' % (pattern.max_age / ctx.intervals.aggr
                if pattern.age_unit == 'usec' else pattern.max_age),
        },
    }

def wops_for_schemes(ctx):
    schemes = ctx.schemes

    schemes_wops = {}
    for scheme in schemes:
        schemes_wops[scheme.name] = {
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
            target.name: {
                'pid_target': '%s' %
                target.pid if _damon.target_has_pid(ctx.ops) else '',
                'regions': wops_for_regions(target.regions)
                } for target in ctx.targets}

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
    return {ctx.name: wops_for_ctx(ctx) for ctx in ctxs}

def wops_for_kdamond(kdamond):
    return {'contexts': wops_for_ctxs(kdamond.contexts)}

def wops_for_kdamonds(kdamonds):
    return {kdamond.name: wops_for_kdamond(kdamond) for kdamond in kdamonds}

def ensure_dirs_populated_for(kdamonds):
    nr_kdamonds, err = _damo_fs.read_file(nr_kdamonds_file)
    if err != None:
        return err
    if int(nr_kdamonds) != len(kdamonds):
        _damo_fs.write_file_ensure(nr_kdamonds_file, '%d' % len(kdamonds))
    for kdamond in kdamonds:
        nr_contexts, err = _damo_fs.read_file(
                nr_contexts_file_of(kdamond.name))
        if err != None:
            return err
        if int(nr_contexts) != len(kdamond.contexts):
            _damo_fs.write_file_ensure(nr_contexts_file_of(kdamond.name),
                    '%d' % len(kdamond.contexts))
        for ctx in kdamond.contexts:
            nr_targets, err = _damo_fs.read_file(
                    nr_targets_file_of(kdamond.name, ctx.name))
            if err != None:
                return err
            if int(nr_targets) != len(ctx.targets):
                _damo_fs.write_file_ensure(
                        nr_targets_file_of(kdamond.name, ctx.name),
                        '%d' % len(ctx.targets))
            for target in ctx.targets:
                nr_regions, err = _damo_fs.read_file(
                        nr_regions_file_of(
                            kdamond.name, ctx.name, target.name))
                if err != None:
                    return err
                if int(nr_regions) != len(target.regions):
                    _damo_fs.write_file_ensure(
                            nr_regions_file_of(
                                kdamond.name, ctx.name, target.name),
                            '%d' % len(target.regions))
        nr_schemes, err = _damo_fs.read_file(
                nr_schemes_file_of(kdamond.name, ctx.name))
        if err != None:
            return err
        if int(nr_schemes) != len(ctx.schemes):
            _damo_fs.write_file_ensure(
                    nr_schemes_file_of(kdamond.name, ctx.name),
                    '%d' % len(ctx.schemes))

def apply_kdamonds(kdamonds):
    if len(kdamonds) > 1:
        print('currently only <=one kdamond is supported')
        exit(1)
    if len(kdamonds) == 1 and len(kdamonds[0].contexts) > 1:
        print('currently only <=one damon_ctx is supported')
        exit(1)
    if (len(kdamonds) == 1 and len(kdamonds[0].contexts) == 1 and
            len(kdamonds[0].contexts[0].targets) > 1):
        print('currently only <=one target is supported')
        exit(1)
    ensure_dirs_populated_for(kdamonds)

    err = _damo_fs.write_files({kdamonds_dir: wops_for_kdamonds(kdamonds)})
    if err != None:
        print('kdamond applying failed: %s' % err)
        traceback.print_exc()
        return 1

# for current_kdamonds()

def files_content_to_access_pattern(files_content):
    return _damon.DamosAccessPattern(
            int(files_content['sz']['min']),
            int(files_content['sz']['max']),
            int(files_content['nr_accesses']['min']),
            int(files_content['nr_accesses']['max']),
            'sample_intervals', # nr_accesses_unit
            int(files_content['age']['min']),
            int(files_content['age']['max']),
            'aggr_intervals') # age_unit

def files_content_to_quotas(files_content):
    return _damon.DamosQuotas(
            int(files_content['ms']),
            int(files_content['bytes']),
            int(files_content['reset_interval_ms']),
            int(files_content['weights']['sz_permil']),
            int(files_content['weights']['nr_accesses_permil']),
            int(files_content['weights']['age_permil']))

def files_content_to_watermarks(files_content):
    return _damon.DamosWatermarks(
            files_content['metric'].strip(),
            int(files_content['interval_us']),
            int(files_content['high']),
            int(files_content['mid']),
            int(files_content['low']))

def files_content_to_damos_stats(files_content):
    return _damon.DamosStats(
            int(files_content['nr_tried']),
            int(files_content['sz_tried']),
            int(files_content['nr_applied']),
            int(files_content['sz_applied']),
            int(files_content['qt_exceeds']))

def files_content_to_damos_tried_regions(files_content):
    regions = []
    for i in range(len(files_content)):
        regions.append(_damon.DamosTriedRegion(
            int(files_content['%d' % i]['start']),
            int(files_content['%d' % i]['end']),
            int(files_content['%d' % i]['nr_accesses']),
            int(files_content['%d' % i]['age']),
            ))
    return regions

def files_content_to_scheme(scheme_name, files_content):
    return _damon.Damos(scheme_name,
            files_content_to_access_pattern(files_content['access_pattern']),
            files_content['action'].strip(),
            files_content_to_quotas(files_content['quotas']),
            files_content_to_watermarks(files_content['watermarks']),
            files_content_to_damos_stats(files_content['stats']),
            files_content_to_damos_tried_regions(
                files_content['tried_regions'])
                if 'tried_regions' in files_content else None)

def files_content_to_regions(files_content):
    regions = []
    for region_idx in range(int(files_content['nr_regions'])):
        region_name = '%d' % region_idx
        regions.append(_damon.DamonRegion(
            int(files_content[region_name]['start']),
            int(files_content[region_name]['end'])))
    return regions

def files_content_to_target(target_name, files_content):
    try:
        pid = int(files_content['pid_target'])
    except:
        pid = None
    regions = files_content_to_regions(files_content['regions'])
    return _damon.DamonTarget(target_name, pid, regions)

def files_content_to_context(context_name, files_content):
    mon_attrs_content = files_content['monitoring_attrs']
    intervals_content = mon_attrs_content['intervals']
    intervals = _damon.DamonIntervals(
            int(intervals_content['sample_us']),
            int(intervals_content['aggr_us']),
            int(intervals_content['update_us']))
    nr_regions_content = mon_attrs_content['nr_regions']
    nr_regions = _damon.DamonNrRegionsRange(
            int(nr_regions_content['min']),
            int(nr_regions_content['max']))
    ops = files_content['operations'].strip()

    targets_content = files_content['targets']
    targets = []
    for target_name in targets_content:
        if target_name == 'nr_targets':
            continue
        targets.append(files_content_to_target(target_name,
            targets_content[target_name]))

    schemes_content = files_content['schemes']
    schemes = []
    for scheme_name in schemes_content:
        if scheme_name == 'nr_schemes':
            continue
        schemes.append(files_content_to_scheme(scheme_name,
            schemes_content[scheme_name]))

    return _damon.DamonCtx(context_name, intervals, nr_regions, ops, targets,
            schemes)

def files_content_to_kdamond(kdamond_name, files_content):
    contexts_content = files_content['contexts']
    contexts = []
    for ctx_name in contexts_content:
        if ctx_name == 'nr_contexts':
            continue
        contexts.append(files_content_to_context(ctx_name,
            contexts_content[ctx_name]))
    state = files_content['state'].strip()
    pid = files_content['pid'].strip()
    return _damon.Kdamond(kdamond_name, state, pid, contexts)

def files_content_to_kdamonds(files_contents):
    kdamonds = []
    for kdamond_name in files_contents:
        if kdamond_name == 'nr_kdamonds':
            continue
        kdamonds.append(files_content_to_kdamond(
            kdamond_name, files_contents[kdamond_name]))
    return kdamonds

def current_kdamonds():
    return files_content_to_kdamonds(
            _damo_fs.read_files_recursive(kdamonds_dir))

def current_kdamond_names():
    # TODO: Do not read recursive but just one depth
    return [x for x in _damo_fs.read_files_recursive(kdamonds_dir).keys()
            if x != 'nr_kdamonds']

def commit_inputs(kdamonds):
    for kdamond in kdamonds:
        err = _damo_fs.write_file(state_file_of(kdamond.name), 'commit')
        if err != None:
            print(err)
            return 1
    return 0

# features

def feature_supported(feature):
    if feature_supports == None:
        update_supported_features()
    return feature_supports[feature]

features_sysfs_support_from_begining = [
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
        'schemes_stat_succ',
        'schemes_stat_qt_exceed',
        ]

def _avail_ops():
    '''Assumes called by update_supported_features() assuming one scheme.
    Returns available ops input and error'''
    avail_ops = []
    avail_operations_filepath = os.path.join(ctx_dir_of(0, 0),
            'avail_operations')
    if not os.path.isfile(avail_operations_filepath):
        operations_filepath = os.path.join(ctx_dir_of(0, 0), 'operations')
        for ops in ['vaddr', 'paddr', 'fvaddr']:
            err = _damo_fs.write_file(operations_filepath, ops)
            if err != None:
                avail_ops.append(ops)
        return avail_ops, None

    content, err = _damo_fs.read_file(avail_operations_filepath)
    if err != None:
        return None, err
    return content.strip().split(), None

def update_supported_features():
    global feature_supports

    if feature_supports != None:
        return None
    feature_supports = {x: False for x in _damon.features}

    if not supported():
        return 'damon sysfs dir (%s) not found' % kdamonds_dir
    for feature in features_sysfs_support_from_begining:
        feature_supports[feature] = True

    orig_kdamonds = None
    if not os.path.isdir(scheme_dir_of(0, 0, 0)):
        orig_kdamonds = current_kdamonds()
        kdamonds_for_feature_check = [_damon.Kdamond(name='0', state=None,
            pid=None, contexts=[_damon.DamonCtx(name='0', intervals=None,
                nr_regions=None, ops=None, targets=[],
                schemes=[_damon.Damos(name='0', access_pattern=None,
                    action='stat', quotas=None, watermarks=None, stats=None)
                    ])])]
        ensure_dirs_populated_for(kdamonds_for_feature_check)

    if os.path.isdir(os.path.join(scheme_dir_of(0, 0, 0), 'tried_regions')):
        feature_supports['schemes_tried_regions'] = True

    avail_ops, err = _avail_ops()
    if err == None:
        for ops in ['vaddr', 'paddr', 'fvaddr']:
            feature_supports[ops] = ops in avail_ops
    if orig_kdamonds != None:
        apply_kdamonds(orig_kdamonds)
    return err
