# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON sysfs control.
"""

import os
import time

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

def ctx_dir_of(kdamond_idx, context_idx):
    return os.path.join(
            kdamond_dir_of(kdamond_idx), 'contexts', '%s' % context_idx)

def schemes_dir_of(kdamond_idx, context_idx):
    return os.path.join(ctx_dir_of(kdamond_idx, context_idx), 'schemes')

def scheme_dir_of(kdamond_idx, context_idx, scheme_idx):
    return os.path.join(
            schemes_dir_of(kdamond_idx, context_idx), '%s' % scheme_idx)

def scheme_tried_regions_dir_of(kdamond_idx, context_idx, scheme_idx):
    return os.path.join(
            scheme_dir_of(kdamond_idx, context_idx, scheme_idx),
            'tried_regions')

def supported():
    return os.path.isdir(kdamonds_dir)

def turn_damon_on(kdamonds_idxs):
    # In case of vaddr, too early monitoring shows unstable mapping changes.
    # Give the process a time to have stable memory mapping.
    time.sleep(0.5)
    for kdamond_idx in kdamonds_idxs:
        err = _damo_fs.write_file(state_file_of(kdamond_idx), 'on')
        if err != None:
            return err
    return None

def turn_damon_off(kdamonds_idxs):
    for kdamond_idx in kdamonds_idxs:
        err = _damo_fs.write_file(state_file_of(kdamond_idx), 'off')
        if err != None:
            return err
    return None

def is_kdamond_running(kdamond_idx):
    content, err = _damo_fs.read_file(state_file_of(kdamond_idx))
    if err != None:
        print(err)
        return False
    return content.strip() == 'on'

'Return error'
def update_schemes_stats(kdamond_idxs):
    for kdamond_idx in kdamond_idxs:
        err = _damo_fs.write_file(
                state_file_of(kdamond_idx), 'update_schemes_stats')
        if err != None:
            return err
    return None

'Return error'
def update_schemes_tried_bytes(kdamond_idxs):
    for kdamond_idx in kdamond_idxs:
        err = _damo_fs.write_file(
                state_file_of(kdamond_idx), 'update_schemes_tried_bytes')
        if err != None:
            return err
    return None

'Return error'
def update_schemes_tried_regions(kdamond_idxs):
    for kdamond_idx in kdamond_idxs:
        err = _damo_fs.write_file(
                state_file_of(kdamond_idx), 'update_schemes_tried_regions')
        if err != None:
            return err
    return None

# for stage_kdamonds

def wops_for_scheme_filter(damos_filter):
    wops = {
        'type': '%s' % damos_filter.filter_type,
        'memcg_path': ('%s' % damos_filter.memcg_path
            if damos_filter.memcg_path != None else ''),
        'matching': 'Y' if damos_filter.matching else 'N',
        }
    if damos_filter.address_range != None:
        wops['addr_start'] = '%d' % damos_filter.address_range.start
        wops['addr_end'] = '%d' % damos_filter.address_range.end
    if damos_filter.damon_target_idx != None:
        wops['damon_target_idx'] = '%d' % damos_filter.damon_target_idx
    return wops

def wops_for_scheme_filters(filters):
    wops = {}
    for idx, damos_filter in enumerate(filters):
        wops['%d' % idx] = wops_for_scheme_filter(damos_filter)
    return wops

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
    pattern = pattern.converted_for_units(
            _damon.unit_samples, _damon.unit_aggr_intervals,
            ctx.intervals)

    return {
        'sz': {
            'min': '%d' % pattern.sz_bytes[0],
            'max': '%d' % pattern.sz_bytes[1],
        },
        'nr_accesses': {
            'min': '%d' % pattern.nr_acc_min_max[0].samples,
            'max': '%d' % pattern.nr_acc_min_max[1].samples,
        },
        'age': {
            'min': '%d' % pattern.age_min_max[0].aggr_intervals,
            'max': '%d' % pattern.age_min_max[1].aggr_intervals,
        },
    }

def wops_for_schemes(ctx):
    schemes = ctx.schemes

    schemes_wops = {}
    for idx, scheme in enumerate(schemes):
        dirname = '%d' % idx
        schemes_wops[dirname] = {
            'access_pattern': wops_for_scheme_access_pattern(
                scheme.access_pattern, ctx),
            'action': scheme.action,
            'quotas': wops_for_scheme_quotas(scheme.quotas),
            'watermarks': wops_for_scheme_watermarks(scheme.watermarks),
        }
        if feature_supported('schemes_filters'):
            schemes_wops[dirname]['filters'] = wops_for_scheme_filters(
                    scheme.filters)
        if feature_supported('schemes_apply_interval'):
            schemes_wops[dirname]['apply_interval_us'] = (
                    '%d' % scheme.apply_interval_us)
    return schemes_wops

def wops_for_regions(regions):
    return {'%d' % region_idx: {
        'start': '%d' % region.start,
        'end': '%d' % region.end}
        for region_idx, region in enumerate(regions)}

def wops_for_targets(ctx):
    return {
            '%d' % idx: {
                'pid_target': '%s' %
                target.pid if _damon.target_has_pid(ctx.ops) else '',
                'regions': wops_for_regions(target.regions)
                } for idx, target in enumerate(ctx.targets)}

def wops_for_monitoring_attrs(ctx):
    return {
        'intervals': {
            'sample_us': '%d' % ctx.intervals.sample,
            'aggr_us': '%d' % ctx.intervals.aggr,
            'update_us': '%d' % ctx.intervals.ops_update,
        },
        'nr_regions': {
            'min': '%d' % ctx.nr_regions.minimum,
            'max': '%d' % ctx.nr_regions.maximum,
        },
    }

def wops_for_ctx(ctx):
    ops = ctx.ops
    if ops == 'fvaddr' and not feature_supported('fvaddr'):
        ops = 'vaddr'
    return [
            {'operations': ops},
            {'monitoring_attrs': wops_for_monitoring_attrs(ctx)},
            {'targets': wops_for_targets(ctx)},
            {'schemes': wops_for_schemes(ctx)},
    ]

def wops_for_ctxs(ctxs):
    return {'%d' % idx: wops_for_ctx(ctx) for idx, ctx in enumerate(ctxs)}

def wops_for_kdamond(kdamond):
    return {'contexts': wops_for_ctxs(kdamond.contexts)}

def wops_for_kdamonds(kdamonds):
    return {'%d' % idx: wops_for_kdamond(kdamond)
            for idx, kdamond in enumerate(kdamonds)}

def __ensure_scheme_dir_populated(scheme_dir, scheme):
    if not feature_supported('schemes_filters'):
        return

    nr_filters_path = os.path.join(scheme_dir, 'filters', 'nr_filters')

    nr_filters, err = _damo_fs.read_file(nr_filters_path)
    if err != None:
        raise Exception('nr_filters read fail (%s)' % err)
    if int(nr_filters) != len(scheme.filters):
        _damo_fs.write_file(nr_filters_path, '%d' % len(scheme.filters))

def __ensure_target_dir_populated(target_dir, target):
    nr_regions_path = os.path.join(target_dir, 'regions', 'nr_regions')
    nr_regions, err = _damo_fs.read_file(nr_regions_path)
    if err != None:
        raise Exception('nr_regions read fail (%s)' % err)
    if int(nr_regions) != len(target.regions):
        _damo_fs.write_file(nr_regions_path, '%d' % len(target.regions))

def __ensure_kdamond_dir_populated(kdamond_dir, kdamond):
    contexts_dir_path = os.path.join(kdamond_dir, 'contexts')
    nr_contexts_path = os.path.join(kdamond_dir, 'contexts', 'nr_contexts')
    nr_contexts, err = _damo_fs.read_file(nr_contexts_path)
    if err != None:
        raise Exception('nr_contexts read fail (%s)' % err)
    if int(nr_contexts) != len(kdamond.contexts):
        _damo_fs.write_file(nr_contexts_path, '%d' % len(kdamond.contexts))

    for ctx_idx, ctx in enumerate(kdamond.contexts):
        ctx_dir_path = os.path.join(contexts_dir_path, '%d' % ctx_idx)
        targets_dir_path = os.path.join(ctx_dir_path, 'targets')
        nr_targets_path = os.path.join(targets_dir_path, 'nr_targets')
        nr_targets, err = _damo_fs.read_file(nr_targets_path)
        if err != None:
            raise Exception('nr_targets read fail (%s)' % err)
        if int(nr_targets) != len(ctx.targets):
            _damo_fs.write_file(nr_targets_path, '%d' % len(ctx.targets))

        for target_idx, target in enumerate(ctx.targets):
            target_dir_path = os.path.join(targets_dir_path, '%d' % target_idx)
            __ensure_target_dir_populated(target_dir_path, target)

        schemes_dir_path = os.path.join(ctx_dir_path, 'schemes')
        nr_schemes_path = os.path.join(schemes_dir_path, 'nr_schemes')
        nr_schemes, err = _damo_fs.read_file(nr_schemes_path)
        if err != None:
            raise Exception('nr_schemes read fail (%s)' % err)
        if int(nr_schemes) != len(ctx.schemes):
            _damo_fs.write_file(nr_schemes_path, '%d' % len(ctx.schemes))

        for scheme_idx, scheme in enumerate(ctx.schemes):
            scheme_dir_path = os.path.join(schemes_dir_path, '%d' % scheme_idx)
            __ensure_scheme_dir_populated(scheme_dir_path, scheme)

def __ensure_dirs_populated_for(kdamonds):
    nr_kdamonds, err = _damo_fs.read_file(nr_kdamonds_file)
    if err != None:
        raise Exception('nr_kdamonds_file read fail (%s)' % err)
    if int(nr_kdamonds) != len(kdamonds):
        _damo_fs.write_file(nr_kdamonds_file, '%d' % len(kdamonds))
    for idx, kdamond in enumerate(kdamonds):
        kdamond_dir = kdamond_dir_of('%d' % idx)
        __ensure_kdamond_dir_populated(kdamond_dir, kdamond)

def ensure_dirs_populated_for(kdamonds):
    try:
        __ensure_dirs_populated_for(kdamonds)
    except Exception as e:
        print('sysfs dirs population failed (%s)' % e)
        exit(1)

def stage_kdamonds(kdamonds):
    if len(kdamonds) == 1 and len(kdamonds[0].contexts) > 1:
        return 'currently only <=one damon_ctx is supported'
    ensure_dirs_populated_for(kdamonds)

    return _damo_fs.write_files({kdamonds_dir: wops_for_kdamonds(kdamonds)})

# for current_kdamonds()

def numbered_dirs_content(files_content, nr_filename):
    nr_dirs = int(files_content[nr_filename])
    number_dirs = []
    for i in range(nr_dirs):
        number_dirs.append(files_content['%d' % i])
    return number_dirs

def number_sorted_dirs(files_content):
    number_dirs = {}
    for filename, content in files_content.items():
        try:
            nr = int(filename)
        except:
            continue
        if type(content) != dict:
            continue
        number_dirs[nr] = content
    sorted_numbers = sorted(number_dirs.keys())
    return [number_dirs[nr] for nr in sorted_numbers]

def files_content_to_access_pattern(files_content):
    return _damon.DamosAccessPattern(
            [int(files_content['sz']['min']),
                int(files_content['sz']['max'])],
            [int(files_content['nr_accesses']['min']),
                int(files_content['nr_accesses']['max'])],
            _damon.unit_samples, # nr_accesses_unit
            [int(files_content['age']['min']),
                int(files_content['age']['max'])],
            _damon.unit_aggr_intervals) # age_unit

def files_content_to_quotas(files_content):
    return _damon.DamosQuotas(
            int(files_content['ms']),
            int(files_content['bytes']),
            int(files_content['reset_interval_ms']),
            [int(files_content['weights']['sz_permil']),
                int(files_content['weights']['nr_accesses_permil']),
                int(files_content['weights']['age_permil'])])

def files_content_to_watermarks(files_content):
    return _damon.DamosWatermarks(
            files_content['metric'].strip(),
            int(files_content['interval_us']),
            int(files_content['high']),
            int(files_content['mid']),
            int(files_content['low']))

def files_content_to_damos_filters(files_content):
    return [_damon.DamosFilter(filter_kv['type'].strip(),
            filter_kv['matching'].strip(),
            filter_kv['memcg_path'].strip(),
            _damon.DamonRegion(filter_kv['addr_start'].strip(),
                filter_kv['addr_end'].strip())
                if 'addr_start' in filter_kv and 'addr_end' in filter_kv
                else None,
            filter_kv['damon_target_idx']
                if 'damon_target_idx' in filter_kv else None)
            for filter_kv in numbered_dirs_content(
                files_content, 'nr_filters')]

def files_content_to_damos_stats(files_content):
    return _damon.DamosStats(
            int(files_content['nr_tried']),
            int(files_content['sz_tried']),
            int(files_content['nr_applied']),
            int(files_content['sz_applied']),
            int(files_content['qt_exceeds']))

def files_content_to_damos_tried_regions(files_content):
    return [_damon.DamonRegion(
            int(kv['start']), int(kv['end']),
            int(kv['nr_accesses']), _damon.unit_samples,
            int(kv['age']), _damon.unit_aggr_intervals)
            for kv in number_sorted_dirs(files_content)]

def files_content_to_scheme(files_content):
    return _damon.Damos(
            files_content_to_access_pattern(files_content['access_pattern']),
            files_content['action'].strip(),
            files_content['apply_interval_us'].strip()
                if 'apply_interval_us' in files_content else None,
            files_content_to_quotas(files_content['quotas']),
            files_content_to_watermarks(files_content['watermarks']),
            files_content_to_damos_filters(files_content['filters'])
                if 'filters' in files_content else [],
            files_content_to_damos_stats(files_content['stats']),
            files_content_to_damos_tried_regions(
                files_content['tried_regions'])
                if 'tried_regions' in files_content else [],
            files_content['tried_regions']['total_bytes']
                if 'tried_regions' in files_content and
                    'total_bytes' in files_content['tried_regions'] else None)

def files_content_to_regions(files_content):
    return [_damon.DamonRegion(
            int(kv['start']), int(kv['end']))
            for kv in numbered_dirs_content(files_content, 'nr_regions')]

def files_content_to_target(files_content):
    try:
        pid = int(files_content['pid_target'])
    except:
        pid = None
    regions = files_content_to_regions(files_content['regions'])
    return _damon.DamonTarget(pid, regions)

def files_content_to_context(files_content):
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
    targets = [files_content_to_target(content)
            for content in numbered_dirs_content(
                targets_content, 'nr_targets')]

    schemes_content = files_content['schemes']
    schemes = [files_content_to_scheme(content)
            for content in numbered_dirs_content(
                schemes_content, 'nr_schemes')]

    return _damon.DamonCtx(ops, targets, intervals, nr_regions, schemes)

def files_content_to_kdamond(files_content):
    contexts_content = files_content['contexts']
    contexts = [files_content_to_context(content)
            for content in numbered_dirs_content(
                contexts_content, 'nr_contexts')]
    state = files_content['state'].strip()
    pid = files_content['pid'].strip()
    return _damon.Kdamond(state, pid, contexts)

def files_content_to_kdamonds(files_contents):
    return [files_content_to_kdamond(content)
            for content in numbered_dirs_content(
                files_contents, 'nr_kdamonds')]

def current_kdamonds():
    return files_content_to_kdamonds(
            _damo_fs.read_files(kdamonds_dir))

def nr_kdamonds():
    nr_kdamonds, err = _damo_fs.read_file(nr_kdamonds_file)
    if err != None:
        raise Exception('nr_kdamonds_file read fail (%s)' % err)
    return int(nr_kdamonds)

def commit_staged(kdamond_idxs):
    for kdamond_idx in kdamond_idxs:
        err = _damo_fs.write_file(state_file_of(kdamond_idx), 'commit')
        if err != None:
            return err
    return None

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
        kdamonds_for_feature_check = [_damon.Kdamond(state=None,
            pid=None, contexts=[_damon.DamonCtx(ops=None, targets=[],
                intervals=None, nr_regions=None,
                schemes=[_damon.Damos(access_pattern=None,
                    action='stat', quotas=None, watermarks=None, filters=[],
                    stats=None)])])]
        ensure_dirs_populated_for(kdamonds_for_feature_check)

    if os.path.isdir(scheme_tried_regions_dir_of(0, 0, 0)):
        feature_supports['schemes_tried_regions'] = True

    if os.path.isfile(os.path.join(scheme_tried_regions_dir_of(0, 0, 0),
            'total_bytes')):
        feature_supports['schemes_tried_regions_sz'] = True

    if os.path.isdir(os.path.join(scheme_dir_of(0, 0, 0), 'filters')):
        feature_supports['schemes_filters'] = True

    if os.path.isfile(os.path.join(scheme_dir_of(0, 0, 0), 'apply_interval_us')):
        feature_supports['schemes_apply_interval'] = True

    avail_ops, err = _avail_ops()
    if err == None:
        for ops in ['vaddr', 'paddr', 'fvaddr']:
            feature_supports[ops] = ops in avail_ops
    if orig_kdamonds != None:
        err = stage_kdamonds(orig_kdamonds)
    return err
