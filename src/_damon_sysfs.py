# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON sysfs control.
"""

import os
import time

import _damo_fs
import _damon

sysfs_root = None

def get_sysfs_root():
    global sysfs_root

    if sysfs_root is None:
        sysfs_root = _damo_fs.dev_mount_point('sysfs')
    return sysfs_root

def get_kdamonds_dir():
    '''Returns None if sysfs is not mounted'''
    if get_sysfs_root() is None:
        return None
    return os.path.join(get_sysfs_root(), 'kernel/mm/damon/admin/kdamonds')

def supported():
    kdamonds_dir = get_kdamonds_dir()
    if kdamonds_dir is None:
        return False
    return os.path.isdir(kdamonds_dir)

def get_state_file_of(kdamond_idx):
    return os.path.join(get_kdamonds_dir(), '%s' % kdamond_idx, 'state')

def __write_state_file(kdamond_idxs, command):
    'Return error'
    err = None
    for kdamond_idx in kdamond_idxs:
        err = _damo_fs.write_file(get_state_file_of(kdamond_idx), command)
        if err != None:
            break
    return err

def turn_damon_on(kdamonds_idxs):
    # In case of vaddr, too early monitoring shows unstable mapping changes.
    # Give the process a time to have stable memory mapping.
    time.sleep(0.5)
    return __write_state_file(kdamonds_idxs, 'on')

def turn_damon_off(kdamonds_idxs):
    return __write_state_file(kdamonds_idxs, 'off')

def is_kdamond_running(kdamond_idx):
    content, err = _damo_fs.read_file(get_state_file_of(kdamond_idx))
    if err != None:
        print(err)
        return False
    return content.strip() == 'on'

'Return error'
def update_schemes_stats(kdamond_idxs):
    return __write_state_file(kdamond_idxs, 'update_schemes_stats')

'Return error'
def update_schemes_tried_bytes(kdamond_idxs):
    err = __write_state_file(kdamond_idxs, 'update_schemes_tried_bytes')
    if err != None:
        err = '%s (maybe schemes_tried_regions_sz not supported?)' % err
    return err

'Return error'
def update_schemes_tried_regions(kdamond_idxs):
    err = __write_state_file(kdamond_idxs, 'update_schemes_tried_regions')
    if err != None:
        err = '%s (maybe schemes_tried_regions not supported?)' % err
    return err

'Return error'
def update_schemes_quota_effective_bytes(kdamond_idxs):
    err = __write_state_file(kdamond_idxs, 'update_schemes_effective_quotas')
    if err != None:
        err = '%s (maybe schemes_effective_quotas not supported?)' % err
    return err

# for stage_kdamonds

def write_filter_dir(dir_path, filter_):
    err = _damo_fs.write_file(
            os.path.join(dir_path, 'type'), filter_.filter_type)
    if err is not None:
        # todo: make error message more detailed.
        # anon/memcg are merged in 6.3-rc1
        # addr/target are merged in 6.6-rc1
        return err

    if filter_.memcg_path is not None:
        err = _damo_fs.write_file(
                os.path.join(dir_path, 'memcg_path'), filter_.memcg_path)
        if err is not None:
            return err

    if filter_.address_range is not None:
        err = _damo_fs.write_file(
                os.path.join(dir_path, 'addr_start'),
                '%d' % filter_.address_range.start)
        if err is not None:
            return err

        err = _damo_fs.write_file(
                os.path.join(dir_path, 'addr_end'),
                '%d' % filter_.address_range.end)
        if err is not None:
            return err

    if filter_.damon_target_idx is not None:
        err = _damo_fs.write_file(
                os.path.join(dir_path, 'damon_target_idx'),
                '%d' % filter_.damon_target_idx)
        if err is not None:
            return err

    return _damo_fs.write_file(os.path.join(dir_path, 'matching'),
                               'Y' if filter_.matching else 'N')

def ensure_nr_file_for(file_path, list_):
    content, err = _damo_fs.read_file(file_path)
    if err is not None:
        return err
    current_nr = int(content)
    desired_nr = len(list_)
    if current_nr == desired_nr:
        return None
    return _damo_fs.write_file(file_path, '%d' % desired_nr)

def write_filters_dir(dir_path, filters):
    # filters merged in v6.3-rc1
    if not os.path.isdir(dir_path):
        if len(filters) == 0:
            return None
        return 'the kernel is not supporting filters'

    err = ensure_nr_file_for(os.path.join(dir_path, 'nr_filters'), filters)
    if err is not None:
        return err

    for idx, filter_ in enumerate(filters):
        err = write_filter_dir(os.path.join(dir_path, '%d' % idx), filter_)
        if err is not None:
            return err
    return None

def write_watermarks_dir(dir_path, wmarks):
    if wmarks is None:
        # TODO: ensure wmarks is not None
        return None
    err = _damo_fs.write_file(os.path.join(dir_path, 'metric'), wmarks.metric)
    if err is not None:
        return err

    err = _damo_fs.write_file(
            os.path.join(dir_path, 'interval_us'), '%d' % wmarks.interval_us)
    if err is not None:
        return err

    err = _damo_fs.write_file(
            os.path.join(dir_path, 'high'), '%d' % wmarks.high_permil)
    if err is not None:
        return err
    err = _damo_fs.write_file(
            os.path.join(dir_path, 'mid'), '%d' % wmarks.mid_permil)
    if err is not None:
        return err
    return _damo_fs.write_file(
            os.path.join(dir_path, 'low'), '%d' % wmarks.low_permil)

def write_quota_goal_dir(dir_path, goal):
    # goal metric is wip as of 6.8-rc4 days.
    if (not os.path.isfile(os.path.join(dir_path, 'target_metric')) and
        goal.metric != 'user_input'):
        return 'the kernel is not supporting quota goal metric'

    if os.path.isfile(os.path.join(dir_path, 'target_metric')):
        err = _damo_fs.write_file(os.path.join(dir_path, 'target_metric'),
                                  '%s' % goal.metric)
        if err is not None:
            return err

    err = _damo_fs.write_file(
            os.path.join(dir_path, 'target_value'),
            '%d' % goal.target_value)
    if err is not None:
        return err

    return _damo_fs.write_file(
            os.path.join(dir_path, 'current_value'),
            '%d' % goal.current_value)

def write_quota_goals_dir(dir_path, goals):
    # goals dir has merged in 6.8-rc1
    if not os.path.isdir(dir_path):
        if len(goals) == 0:
            return None
        return 'the kernel is not supporting schemes quota goals'

    err = ensure_nr_file_for(os.path.join(dir_path, 'nr_goals'), goals)
    if err is not None:
        return err

    for idx, goal in enumerate(goals):
        err = write_quota_goal_dir(os.path.join(dir_path, '%d' % idx), goal)
        if err is not None:
            return err
    return None

def write_quota_weights_dir(dir_path, quotas):
    err = _damo_fs.write_file(os.path.join(dir_path, 'sz_permil'),
                              '%d' % quotas.weight_sz_permil)
    if err is not None:
        return err

    err = _damo_fs.write_file(os.path.join(dir_path, 'nr_accesses_permil'),
                              '%d' % quotas.weight_nr_accesses_permil)
    if err is not None:
        return err

    return _damo_fs.write_file(os.path.join(dir_path, 'age_permil'),
                              '%d' % quotas.weight_age_permil)

def write_quotas_dir(dir_path, quotas):
    err = _damo_fs.write_file(
            os.path.join(dir_path, 'ms'), '%d' % quotas.time_ms)
    if err is not None:
        return err

    err = _damo_fs.write_file(
            os.path.join(dir_path, 'bytes'), '%d' % quotas.sz_bytes)
    if err is not None:
        return err

    err = _damo_fs.write_file(os.path.join(dir_path, 'reset_interval_ms'),
                              '%d' % quotas.reset_interval_ms)
    if err is not None:
        return err

    err = write_quota_weights_dir(os.path.join(dir_path, 'weights'), quotas)
    if err is not None:
        return err

    return write_quota_goals_dir(os.path.join(dir_path, 'goals'), quotas.goals)

def write_scheme_access_pattern_dir(dir_path, pattern):
    err = _damo_fs.write_file(
            os.path.join(dir_path, 'sz', 'min'), '%d' % pattern.sz_bytes[0])
    if err is not None:
        return err

    err = _damo_fs.write_file(
            os.path.join(dir_path, 'sz', 'max'), '%d' % pattern.sz_bytes[1])
    if err is not None:
        return err

    err = _damo_fs.write_file(os.path.join(dir_path, 'nr_accesses', 'min'),
                              '%d' % pattern.nr_acc_min_max[0].samples)
    if err is not None:
        return err

    err = _damo_fs.write_file(os.path.join(dir_path, 'nr_accesses', 'max'),
                              '%d' % pattern.nr_acc_min_max[1].samples)
    if err is not None:
        return err

    err = _damo_fs.write_file(os.path.join(dir_path, 'age', 'min'),
                              '%d' % pattern.age_min_max[0].aggr_intervals)
    if err is not None:
        return err
    return _damo_fs.write_file(os.path.join(dir_path, 'age', 'max'),
                              '%d' % pattern.age_min_max[1].aggr_intervals)

def write_scheme_dir(dir_path, scheme):
    err = write_scheme_access_pattern_dir(
            os.path.join(dir_path, 'access_pattern'), scheme.access_pattern)
    if err is not None:
        return err

    err = _damo_fs.write_file(os.path.join(dir_path, 'action'), scheme.action)
    if err is not None:
        return err

    err = write_quotas_dir(os.path.join(dir_path, 'quotas'), scheme.quotas)
    if err is not None:
        return err

    err = write_watermarks_dir(
            os.path.join(dir_path, 'watermarks'), scheme.watermarks)
    if err is not None:
        return err

    err = write_filters_dir(os.path.join(dir_path, 'filters'), scheme.filters)
    if err is not None:
        return err

    apply_interval_file = os.path.join(dir_path, 'apply_interval_us')
    # schemes apply interval is merged in v6.7-rc1
    if os.path.isfile(apply_interval_file):
        err = _damo_fs.write_file(apply_interval_file,
                                  '%d' % scheme.apply_interval_us)
        if err is not None:
            return err
    else:
        if scheme.apply_interval_us:
            return 'the kernel is not supporting schemes apply interval'
    return None

def write_schemes_dir(dir_path, schemes):
    err = ensure_nr_file_for(os.path.join(dir_path, 'nr_schemes'), schemes)
    if err is not None:
        return err

    for idx, scheme in enumerate(schemes):
        err = write_scheme_dir(os.path.join(dir_path, '%d' % idx), scheme)
        if err is not None:
            return err

def write_target_region_dir(dir_path, region):
    err = _damo_fs.write_file(
            os.path.join(dir_path, 'start'), '%d' % region.start)
    if err is not None:
        return err

    return _damo_fs.write_file(
            os.path.join(dir_path, 'end'), '%d' % region.end)

def write_target_regions_dir(dir_path, regions):
    err = ensure_nr_file_for(os.path.join(dir_path, 'nr_regions'), regions)
    if err is not None:
        return err

    for idx, region in enumerate(regions):
        err = write_target_region_dir(
                os.path.join(dir_path, '%d' % idx), region)
        if err is not None:
            return err
    return None

def write_target_dir(dir_path, target):
    if target.pid is not None:
        err = _damo_fs.write_file(
                os.path.join(dir_path, 'pid_target'), '%s' % target.pid)
        if err is not None:
            return err

    return write_target_regions_dir(
            os.path.join(dir_path, 'regions'), target.regions)


def write_targets_dir(dir_path, targets):
    err = ensure_nr_file_for(os.path.join(dir_path, 'nr_targets'), targets)
    if err is not None:
        return err

    for idx, target in enumerate(targets):
        err = write_target_dir(os.path.join(dir_path, '%d' % idx), target)
        if err is not None:
            return err
    return None

def write_monitoring_attrs_dir(dir_path, context):
    err = _damo_fs.write_file(
            os.path.join(dir_path, 'intervals', 'sample_us'),
            '%d' % context.intervals.sample)
    if err is not None:
        return err

    err = _damo_fs.write_file(
            os.path.join(dir_path, 'intervals', 'aggr_us'),
            '%d' % context.intervals.aggr)
    if err is not None:
        return err

    err = _damo_fs.write_file(
            os.path.join(dir_path, 'intervals', 'update_us'),
            '%d' % context.intervals.ops_update)
    if err is not None:
        return err

    err = _damo_fs.write_file(
            os.path.join(dir_path, 'nr_regions', 'min'),
            '%d' % context.nr_regions.minimum)
    if err is not None:
        return err

    return _damo_fs.write_file(
            os.path.join(dir_path, 'nr_regions', 'max'),
            '%d' % context.nr_regions.maximum)

def write_context_dir(dir_path, context):
    err = _damo_fs.write_file(os.path.join(dir_path, 'operations'),
                              context.ops)
    if err is not None:
        return err

    err = write_monitoring_attrs_dir(
            os.path.join(dir_path, 'monitoring_attrs'), context)
    if err is not None:
        return err

    err = write_targets_dir(
            os.path.join(dir_path, 'targets'), context.targets)
    if err is not None:
        return err

    for scheme in context.schemes:
        scheme.access_pattern = scheme.access_pattern.converted_for_units(
                _damon.unit_samples, _damon.unit_aggr_intervals,
                context.intervals)
    return write_schemes_dir(
            os.path.join(dir_path, 'schemes'), context.schemes)

def write_contexts_dir(dir_path, contexts):
    err = ensure_nr_file_for(os.path.join(dir_path, 'nr_contexts'), contexts)
    if err is not None:
        return err

    for idx, context in enumerate(contexts):
        err = write_context_dir(
                os.path.join(dir_path, '%d' % idx), context)
        if err is not None:
            return err

def write_kdamonds_dir(dir_path, kdamonds):
    err = ensure_nr_file_for(os.path.join(dir_path, 'nr_kdamonds'), kdamonds)
    if err:
        return err

    for idx, kdamond in enumerate(kdamonds):
        err = write_contexts_dir(
                os.path.join(dir_path, '%d' % idx, 'contexts'),
                kdamond.contexts)
        if err is not None:
            return err

def stage_kdamonds(kdamonds):
    """Write DAMON parameters for kdamonds to the sysfs files.

    Args:
        kdamonds: A list of _damon.Kdamond objects.

    Returns:
        None for success, an error string if failed.
    """
    # Assume caller checked supported()
    return write_kdamonds_dir(get_kdamonds_dir(), kdamonds)

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

def files_content_to_quota_goals(files_content):
    goals = []
    for goal_kv in number_sorted_dirs(files_content):
        if 'target_metric' in goal_kv:
            goals.append(
                    _damon.DamosQuotaGoal(
                        metric=goal_kv['target_metric'].strip(),
                        target_value=goal_kv['target_value'],
                        current_value=goal_kv['current_value']))
        else:
            goals.append(
                    _damon.DamosQuotaGoal(
                        target_value=goal_kv['target_value'],
                        current_value=goal_kv['current_value']))
    return goals

def files_content_to_quotas(files_content):
    return _damon.DamosQuotas(
            int(files_content['ms']),
            int(files_content['bytes']),
            int(files_content['reset_interval_ms']),
            [int(files_content['weights']['sz_permil']),
                int(files_content['weights']['nr_accesses_permil']),
                int(files_content['weights']['age_permil'])],
            files_content_to_quota_goals(files_content['goals'])
            if 'goals' in files_content else [],
            int(files_content['effective_bytes'])
            if 'effective_bytes' in files_content else 0)

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
    # Assume caller checked supported()
    return files_content_to_kdamonds(_damo_fs.read_files(get_kdamonds_dir()))

def get_nr_kdamonds_file():
    return os.path.join(get_kdamonds_dir(), 'nr_kdamonds')

def nr_kdamonds():
    nr_kdamonds, err = _damo_fs.read_file(get_nr_kdamonds_file())
    if err != None:
        raise Exception('nr_kdamonds_file read fail (%s)' % err)
    return int(nr_kdamonds)

def commit_staged(kdamond_idxs):
    for kdamond_idx in kdamond_idxs:
        err = _damo_fs.write_file(get_state_file_of(kdamond_idx), 'commit')
        if err != None:
            return err
    return None

def commit_quota_goals(kdamond_idxs):
    for kdamond_idx in kdamond_idxs:
        err = _damo_fs.write_file(get_state_file_of(kdamond_idx),
                'commit_schemes_quota_goals')
        if err != None:
            return err

# features

feature_supports = None

def feature_supported(feature):
    if feature_supports == None:
        update_supported_features()
    return feature_supports[feature]

# sysfs was merged in v5.18-rc1
features_sysfs_support_from_begining = [
        'schemes',
        'init_regions',
        'vaddr',
        'paddr',
        'init_regions_target_idx',
        'schemes_speed_limit',
        'schemes_quotas',
        'schemes_prioritization',
        'schemes_wmarks',
        'schemes_stat_succ',
        'schemes_stat_qt_exceed',
        ]

def kdamond_dir_of(kdamond_idx):
    return os.path.join(get_kdamonds_dir(), '%s' % kdamond_idx)

def ctx_dir_of(kdamond_idx, context_idx):
    return os.path.join(
            kdamond_dir_of(kdamond_idx), 'contexts', '%s' % context_idx)

def schemes_dir_of(kdamond_idx, context_idx):
    return os.path.join(ctx_dir_of(kdamond_idx, context_idx), 'schemes')

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

def scheme_dir_of(kdamond_idx, context_idx, scheme_idx):
    return os.path.join(
            schemes_dir_of(kdamond_idx, context_idx), '%s' % scheme_idx)

def scheme_tried_regions_dir_of(kdamond_idx, context_idx, scheme_idx):
    return os.path.join(
            scheme_dir_of(kdamond_idx, context_idx, scheme_idx),
            'tried_regions')

def infer_damon_version():
    version = '<5.15'
    orig_kdamonds = current_kdamonds()
    kdamonds = [
            _damon.Kdamond(
                state=None, pid=None, contexts=[
                    _damon.DamonCtx(
                        schemes=[
                            _damon.Damos(
                                filters=[_damon.DamosFilter('young', True)]
                                )])])]
    err = stage_kdamonds(kdamonds)
    if err is None:
        err = stage_kdamonds(orig_kdamonds)
        return '>6.9'

    kdamonds[0].contexts[0].schemes[0].filters = []
    err = stage_kdamonds(kdamonds)

    if os.path.isfile(os.path.join(scheme_dir_of(0, 0, 0), 'quotas',
                                   'effective_bytes')):
        stage_kdamonds(orig_kdamonds)
        return '6.9'

    if os.path.isdir(os.path.join(scheme_dir_of(0, 0, 0), 'quotas', 'goals')):
        stage_kdamonds(orig_kdamonds)
        return '6.8'

    if os.path.isfile(os.path.join(scheme_dir_of(0, 0, 0), 'apply_interval_us')):
        stage_kdamonds(orig_kdamonds)
        return '6.7'

    if os.path.isfile(os.path.join(scheme_tried_regions_dir_of(0, 0, 0),
            'total_bytes')):
        stage_kdamonds(orig_kdamonds)
        return '6.6'

    if os.path.isdir(os.path.join(scheme_dir_of(0, 0, 0), 'filters')):
        stage_kdamonds(orig_kdamonds)
        return '6.3'

    if os.path.isdir(scheme_tried_regions_dir_of(0, 0, 0)):
        stage_kdamonds(orig_kdamonds)
        return '6.2'

    stage_kdamonds(orig_kdamonds)
    return '<6.2'

def update_supported_features():
    global feature_supports

    if feature_supports != None:
        return None
    feature_supports = {x: False for x in _damon.features}

    if not supported():
        return 'damon sysfs not supported'
    for feature in features_sysfs_support_from_begining:
        feature_supports[feature] = True

    orig_kdamonds = current_kdamonds()
    kdamonds_for_feature_check = [
            _damon.Kdamond(
                state=None, pid=None, contexts=[
                    _damon.DamonCtx(
                        schemes=[_damon.Damos()])])]
    err = stage_kdamonds(kdamonds_for_feature_check)
    if err is not None:
        print('staging feature check purpose kdamond failed')
        stage_kdamonds(orig_kdamonds)
        exit(1)

    if os.path.isdir(scheme_tried_regions_dir_of(0, 0, 0)):
        feature_supports['schemes_tried_regions'] = True

    if os.path.isfile(os.path.join(scheme_tried_regions_dir_of(0, 0, 0),
            'total_bytes')):
        feature_supports['schemes_tried_regions_sz'] = True
        # address and target filter types are added in v6.6-rc1, together with
        # schemes_tried_regions_sz
        feature_supports['schemes_filters_addr'] = True
        feature_supports['schemes_filters_target'] = True

    if os.path.isdir(os.path.join(scheme_dir_of(0, 0, 0), 'filters')):
        feature_supports['schemes_filters'] = True
        # anon and memcg were supported from the beginning
        feature_supports['schemes_filters_anon'] = True
        feature_supports['schemes_filters_memcg'] = True
        kdamonds_for_feature_check[0].contexts[0].schemes[0].filters = [
                _damon.DamosFilter('young', True)]
        err = stage_kdamonds(kdamonds_for_feature_check)
        if err is None:
            feature_supports['schemes_filters_young'] = True

    if os.path.isfile(os.path.join(scheme_dir_of(0, 0, 0), 'apply_interval_us')):
        feature_supports['schemes_apply_interval'] = True

    if os.path.isdir(os.path.join(scheme_dir_of(0, 0, 0), 'quotas', 'goals')):
        feature_supports['schemes_quota_goals'] = True

    if os.path.isfile(os.path.join(scheme_dir_of(0, 0, 0), 'quotas',
                                   'effective_bytes')):
        feature_supports['schemes_quota_effective_bytes'] = True
        # goal_metric and goal_some_psi will be merged together with effective bytes.
        feature_supports['schemes_quota_goal_metric'] = True
        feature_supports['schemes_quota_goal_some_psi'] = True

    avail_ops, err = _avail_ops()
    if err == None:
        for ops in ['vaddr', 'paddr', 'fvaddr']:
            feature_supports[ops] = ops in avail_ops
    err = stage_kdamonds(orig_kdamonds)
    return err
