# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON debugfs control.
"""

import os

import _damo_deprecation_notice
import _damo_fs
import _damon

debugfs_root = None

def get_debugfs_root():
    global debugfs_root

    if debugfs_root is None:
        debugfs_root = _damo_fs.dev_mount_point('debugfs')
    return debugfs_root

def get_damon_dir():
    '''Returns None if debugfs is not mounted'''
    if get_debugfs_root() is None:
        return None
    return os.path.join(get_debugfs_root(), 'damon')

def get_debugfs_monitor_on_path():
    path = os.path.join(get_damon_dir(), 'monitor_on')
    if os.path.isfile(path):
        return path
    path = os.path.join(get_damon_dir(), 'monitor_on_DEPRECATED')
    if os.path.isfile(path):
        return path
    return None

def supported():
    damon_dir = get_damon_dir()
    if damon_dir is None:
        return False
    return os.path.isdir(damon_dir)

def turn_damon_on(kdamonds_idxs):
    return _damo_fs.write_file(get_debugfs_monitor_on_path(), 'on')

def turn_damon_off(kdamonds_idxs):
    return _damo_fs.write_file(get_debugfs_monitor_on_path(), 'off')

def is_kdamond_running(kdamond_idx):
    content, err = _damo_fs.read_file(get_debugfs_monitor_on_path())
    if err != None:
        raise Exception('monitor_on file read failed: err')
    return content.strip() == 'on'

'Return error'
def update_schemes_stats(kdamond_idxs):
    # DAMON debugfs updates stats always
    return None

def update_schemes_tried_regions(kdamond_idxs):
    return 'DAMON debugfs doesn\'t support schemes tried regions'

def update_schemes_quota_effective_bytes(kdamond_idxs):
    return 'DAMON debugfs doesn\'t support schemes effective quota'

# for stage_kdamonds

# note that DAMON debugfs interface is deprecated[1], and hence newer DAMOS
# actions including _damon.damos_action_lru_prio and
# _damon.damos_action_lru_deprio are not supported.
#
# [1] https://git.kernel.org/torvalds/c/5445fcbc4cda
damos_action_to_int = {
        _damon.damos_action_willneed: 0,
        _damon.damos_action_cold: 1,
        _damon.damos_action_pageout: 2,
        _damon.damos_action_hugepage: 3,
        _damon.damos_action_nohugepage: 4,
        _damon.damos_action_stat: 5}

damos_wmark_metric_to_int = {
        _damon.damos_wmarks_metric_none: 0,
        _damon.damos_wmarks_metric_free_mem_rate: 1}

def damos_action_to_file_input(action_str):
    if not action_str in damos_action_to_int:
        raise Exception('\'%s\' DAMOS action is not supported' % action_str)
    return damos_action_to_int[action_str]

def damos_wmarks_metric_to_file_input(metric_str):
    if not metric_str in damos_wmark_metric_to_int:
        raise Exception('\'%s\' DAMOS watermark metric is not supported' %
                metric_str)
    return damos_wmark_metric_to_int[metric_str]

def file_content_to_damos_action(action_file_content):
    for action_str in damos_action_to_int:
        if damos_action_to_int[action_str] == action_file_content:
            return action_str

def file_content_to_damos_wmarks_metric(metric_file_content):
    for metric_str in damos_wmark_metric_to_int:
        if damos_wmark_metric_to_int[metric_str] == metric_file_content:
            return metric_str

def damos_to_debugfs_input(damos, intervals, quotas_wmarks_supported):
    pattern = damos.access_pattern.converted_for_units(
            _damon.unit_samples, _damon.unit_aggr_intervals,
            intervals)
    quotas = damos.quotas
    watermarks = damos.watermarks

    max_nr_accesses = intervals.aggr / intervals.sample
    scheme_input = '%d\t%d\t%d\t%d\t%d\t%d\t%d' % (
            pattern.sz_bytes[0], pattern.sz_bytes[1],
            pattern.nr_acc_min_max[0].samples,
            pattern.nr_acc_min_max[1].samples,
            pattern.age_min_max[0].aggr_intervals,
            pattern.age_min_max[1].aggr_intervals,
            damos_action_to_file_input(damos.action))
    if not quotas_wmarks_supported:
        return scheme_input

    scheme_input = '%s\t' % scheme_input + '\t'.join(
            '%d' % x for x in [
                # quotas
                quotas.time_ms, quotas.sz_bytes, quotas.reset_interval_ms,
                quotas.weight_sz_permil, quotas.weight_nr_accesses_permil,
                quotas.weight_age_permil,
                # wmarks
                damos_wmarks_metric_to_file_input(watermarks.metric),
                watermarks.interval_us, watermarks.high_permil,
                watermarks.mid_permil, watermarks.low_permil])
    return scheme_input

def write_schemes(dir_path, schemes, intervals):
    scheme_file_input_lines = []
    for scheme in schemes:
        scheme_file_input_lines.append(damos_to_debugfs_input(scheme,
            intervals, feature_supported('schemes_quotas')))
    scheme_file_input = '\n'.join(scheme_file_input_lines)
    if scheme_file_input == '':
        scheme_file_input = '\n'
    err = _damo_fs.write_file(
            os.path.join(dir_path, 'schemes'), scheme_file_input)

def write_target(dir_path, target, target_has_pid):
    if target_has_pid:
        err = _damo_fs.write_file(
                os.path.join(dir_path, 'target_ids'), '%s' % target.pid)
        if err is not None:
            return err
        tid = target.pid
    else:
        if not feature_supported('paddr'):
            raise Exception('paddr is not supported')
        err = _damo_fs.write_file(
                os.path.join(dir_path, 'target_ids'), 'paddr\n')
        if err is not None:
            return err
        tid = 42
    if feature_supported('init_regions_target_idx'):
        tid = 0

    if feature_supported('init_regions'):
        string = ' '.join(['%s %d %d' % (tid, r.start, r.end) for r in
            target.regions])
        err = _damo_fs.write_file(
                os.path.join(dir_path, 'init_regions'), string)
        if err is not None:
            return err
    return None

def attr_str_ctx(damon_ctx):
    intervals = damon_ctx.intervals
    nr_regions = damon_ctx.nr_regions
    return '%d %d %d %d %d ' % (intervals.sample, intervals.aggr,
            intervals.ops_update, nr_regions.minimum, nr_regions.maximum)

def write_kdamonds(dir_path, kdamonds):
    if len(kdamonds) > 1:
        raise Exception('Currently only <=one kdamond is supported')
    if len(kdamonds) == 1 and len(kdamonds[0].contexts) > 1:
        raise Exception('currently only <= one damon_ctx is supported')
    if (len(kdamonds) == 1 and len(kdamonds[0].contexts) == 1 and
            len(kdamonds[0].contexts[0].targets) > 1):
        raise Exception('currently only <= one target is supported')
    ctx = kdamonds[0].contexts[0]

    err = _damo_fs.write_file(
            os.path.join(dir_path, 'attrs'), attr_str_ctx(ctx))
    if err is not None:
        return err

    if len(ctx.targets) > 0:
        err = write_target(
                dir_path, ctx.targets[0], _damon.target_has_pid(ctx.ops))
        if err:
            return err
    if not feature_supported('schemes'):
        return None

    err = write_schemes(dir_path, ctx.schemes, ctx.intervals)
    return err

def stage_kdamonds(kdamonds):
    '''Return error'''
    if _damon.any_kdamond_running():
        return 'DAMON debugfs doesn\'t support online staging'

    return write_kdamonds(get_damon_dir(), kdamonds)

# for current_kdamonds

def debugfs_schemes_output_fields_to_access_pattern(fields, intervals_us):
    sz_bytes = fields[:2]

    # convert nr_accesses from sample intervals to percent
    max_nr_accesses = intervals_us.aggr / intervals_us.sample
    nr_accesses = [float(fields[2]) * 100 / max_nr_accesses,
            float(fields[3]) * 100 / max_nr_accesses]
    nr_accesses_unit = _damon.unit_percent

    # convert ages in update_interval to us
    age = [intervals_us.aggr * fields[4], intervals_us.aggr * fields[5]]
    age_unit = _damon.unit_usec

    return _damon.DamosAccessPattern(sz_bytes, nr_accesses, nr_accesses_unit,
            age, age_unit)

def debugfs_output_to_damos(output, intervals_us):
    fields = [int(x) for x in output.strip().split()]
    if feature_supported('schemes_stat_succ'):
        nr_stat_fields = 5
    else:
        nr_stat_fields = 2
    stat_fields = fields[-1 * nr_stat_fields:]
    fields = [int(x) for x in output.strip().split()][:-1 * nr_stat_fields]

    access_pattern = debugfs_schemes_output_fields_to_access_pattern(fields,
            intervals_us)
    action = file_content_to_damos_action(fields[6])

    if len(fields) == 7:
        damos = _damon.Damos(access_pattern=access_pattern, action=action)
    elif len(fields) == 18:
        damos = _damon.Damos(access_pattern=access_pattern, action=action)
        damos.quotas.time_ms = fields[7]
        damos.quotas.sz_bytes = fields[8]
        damos.quotas.reset_interval_ms = fields[9]
        damos.quotas.weight_sz_permil = fields[10]
        damos.quotas.weight_nr_accesses_permil = fields[11]
        damos.quotas.weight_age_permil = fields[12]
        damos.watermarks.metric = file_content_to_damos_wmarks_metric(
                fields[13])
        damos.watermarks.interval_us = fields[14]
        damos.watermarks.high_permil = fields[15]
        damos.watermarks.mid_permil = fields[16]
        damos.watermarks.low_permil = fields[17]
    damos.stats = _damon.DamosStats(*stat_fields)
    return damos

def files_content_to_kdamonds(files_content):
    if 'monitor_on' in files_content:
        state = files_content['monitor_on'].strip()
    else:
        state = files_content['monitor_on_DEPRECATED'].strip()
    attrs = [int(x) for x in files_content['attrs'].strip().split()]

    intervals = _damon.DamonIntervals(attrs[0], attrs[1], attrs[2])
    nr_regions = _damon.DamonNrRegionsRange(attrs[3], attrs[4])

    target_ids = [int(x) for x in files_content['target_ids'].strip().split()]
    regions_dict = {}
    # Reading init_regions fails when DAMON is running.  Do the parsing only
    # when DAMON is off.
    if state == 'off' and feature_supported('init_regions'):
        fields = [int(x) for x in files_content['init_regions'].strip().split()]
        for i in range(0, len(fields), 3):
            id_or_index = fields[i]
            if not id_or_index in regions_dict:
                regions_dict[id_or_index] = []
            regions_dict[id_or_index].append(_damon.DamonRegion(
                    fields[i + 1], fields[i + 2]))
    ops = 'vaddr'
    is_paddr = False
    if 42 in target_ids:
        ops = 'paddr'
    targets = []
    for idx, target_id in enumerate(target_ids):
        targets.append(_damon.DamonTarget(
            pid=target_id if not is_paddr else None,
            regions=regions_dict[idx
                if feature_supported('init_regions_target_idx')
                else target_id] if len(regions_dict) > 0 else []))

    schemes = []
    if feature_supported('schemes'):
        for line in files_content['schemes'].split('\n'):
            if line.strip() == '':
                continue
            schemes.append(debugfs_output_to_damos(line, intervals))

    ctx = _damon.DamonCtx(ops, targets, intervals, nr_regions, schemes)
    if 'monitor_on' in files_content:
        state = files_content['monitor_on'].strip()
    else:
        state = files_content['monitor_on_DEPRECATED'].strip()
    pid = files_content['kdamond_pid'].strip()
    return [_damon.Kdamond(state, pid, [ctx])]

def current_kdamonds():
    return files_content_to_kdamonds(
            _damo_fs.read_files(get_damon_dir()))

def nr_kdamonds():
    # TODO: Support manually created kdamonds
    return 1

# features

feature_supports = None

def feature_supported(feature):
    if feature_supports == None:
        update_supported_features()

    return feature_supports[feature]

def values_for_restore(filepath, read_val):
    if read_val == '':
        return '\n'
    if os.path.basename(filepath) == 'target_ids' and read_val == '42\n':
        return 'paddr\n'
    return read_val

'''Return value to write back to the filepath for restoring, and error'''
def read_value_for_restore(filepath):
    err = True
    read_val, err = _damo_fs.read_file(filepath)
    if err != None:
        return None, err
    err = None
    return values_for_restore(filepath, read_val), err

def test_debugfs_file(path, input_str, expected):
    orig_val, err = read_value_for_restore(path)
    if err != None:
        return False
    err = _damo_fs.write_file(path, input_str)
    if err != None:
        return False
    content, err = _damo_fs.read_file(path)
    if err != None:
        return False
    if content == expected:
        passed = True
    else:
        passed = False
    err = _damo_fs.write_file(path, orig_val)
    if err != None:
        return False
    return passed

def get_schemes_file():
    return os.path.join(get_damon_dir(), 'schemes')

def test_debugfs_file_schemes(nr_fields):
    input_str = ' '.join(['1'] * nr_fields)
    expected = '%s 0 0\n' % input_str

    return test_debugfs_file(get_schemes_file(), input_str, expected)

def test_debugfs_file_schemes_stat_extended(nr_fields):
    input_str = ' '.join(['1'] * nr_fields)
    expected = '%s 0 0 0 0 0\n' % input_str

    return test_debugfs_file(get_schemes_file(), input_str, expected)

def get_target_ids_file():
    return os.path.join(get_damon_dir(), 'target_ids')

def get_init_regions_file():
    return os.path.join(get_damon_dir(), 'init_regions')

def test_init_regions_version(paddr_supported):
    # Save previous values
    orig_target_ids, err = read_value_for_restore(get_target_ids_file())
    if err != None:
        raise Exception('debugfs target_ids read failed')
    orig_init_regions, err = read_value_for_restore(get_init_regions_file())
    if err != None:
        raise Exception('debugfs init_regions read failed')

    # Test
    if paddr_supported:
        err = _damo_fs.write_file(get_target_ids_file(), 'paddr\n')
        if err != None:
            raise Exception(err)
        v1_input = '42 100 200'
    else:
        err = _damo_fs.write_file(get_target_ids_file(), '%d\n' % os.getpid())
        if err != None:
            raise Exception(err)
        v1_input = '%d 100 200' % os.getpid()

    # We check if the write was success below anyway, so ignore error
    err = _damo_fs.write_file(get_init_regions_file(), v1_input)
    read_val, err = _damo_fs.read_file(get_init_regions_file())
    if err != None:
        raise Exception(err)
    if read_val.strip() == v1_input:
        version = 1
    else:
        version = 2

    # Previous value might be invalid now (e.g., process terminated), so ignore
    # error
    err = _damo_fs.write_file(get_target_ids_file(), orig_target_ids)
    err = _damo_fs.write_file(get_init_regions_file(), orig_init_regions)

    return version

def update_supported_features():
    global feature_supports
    if feature_supports != None:
        return None
    feature_supports = {x: False for x in _damon.features}

    if not os.path.isdir(get_damon_dir()):
        return 'damon debugfs dir (%s) not found' % get_damon_dir()

    need_schemes_file_test = False
    if os.path.isfile(get_schemes_file()):
        feature_supports['schemes'] = True
        with open(get_schemes_file(), 'r') as f:
            nr_fields = len(f.read().strip().split())
        if nr_fields == 0:
            need_schemes_file_test = True
        elif nr_fields == 20:   # v5.16
            feature_supports['schemes_speed_limit'] = True
            feature_supports['schemes_prioritization'] = True
            feature_supports['schemes_wmarks'] = True
            feature_supports['schemes_quotas'] = True
        elif nr_fields == 23:   # v5.17 or later
            feature_supports['schemes_speed_limit'] = True
            feature_supports['schemes_prioritization'] = True
            feature_supports['schemes_wmarks'] = True
            feature_supports['schemes_quotas'] = True
            feature_supports['schemes_stat_succ'] = True
            feature_supports['schemes_stat_qt_exceed'] = True

    if _damon.any_kdamond_running():
        return 'debugfs feature update cannot be done while DAMON running'

    # virtual address space has supported since the beginning
    feature_supports['vaddr'] = True
    if test_debugfs_file(get_target_ids_file(), 'paddr\n', '42\n'):
        feature_supports['paddr'] = True

    if os.path.isfile(get_init_regions_file()):
        feature_supports['init_regions'] = True
        init_regions_version = test_init_regions_version(
                feature_supports['paddr'])
        if init_regions_version == 2:
            feature_supports['init_regions_target_idx'] = True

    if need_schemes_file_test:
        # 'schemes' receives 18 numbers input and has three stats (v5.16)
        if test_debugfs_file_schemes(18):
            feature_supports['schemes_speed_limit'] = True
            feature_supports['schemes_prioritization'] = True
            feature_supports['schemes_wmarks'] = True
            feature_supports['schemes_quotas'] = True
        elif test_debugfs_file_schemes_stat_extended(18):
            feature_supports['schemes_speed_limit'] = True
            feature_supports['schemes_prioritization'] = True
            feature_supports['schemes_wmarks'] = True
            feature_supports['schemes_quotas'] = True
            feature_supports['schemes_stat_succ'] = True
            feature_supports['schemes_stat_qt_exceed'] = True

    return None
