# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON debugfs control.
"""

import os

import _damo_deprecation_notice
import _damo_fs
import _damon

debugfs = '/sys/kernel/debug'
debugfs_damon = os.path.join(debugfs, 'damon')
debugfs_attrs = os.path.join(debugfs_damon, 'attrs')
debugfs_schemes = os.path.join(debugfs_damon, 'schemes')
debugfs_target_ids = os.path.join(debugfs_damon, 'target_ids')
debugfs_init_regions = os.path.join(debugfs_damon, 'init_regions')
debugfs_monitor_on = os.path.join(debugfs_damon, 'monitor_on')

def turn_damon_on(kdamonds_idxs):
    return _damo_fs.write_files({debugfs_monitor_on: 'on'})

def turn_damon_off(kdamonds_idxs):
    return _damo_fs.write_files({debugfs_monitor_on: 'off'})

def is_kdamond_running(kdamond_idx):
    content, err = _damo_fs.read_file(debugfs_monitor_on)
    if err != None:
        raise Exception('monitor_on file read failed: err')
    return content.strip() == 'on'

'Return error'
def update_schemes_stats(kdamond_idxs):
    # DAMON debugfs updates stats always
    return None

def update_schemes_tried_regions(kdamond_idxs):
    return 'DAMON debugfs doesn\'t support schemes tried regions'

# for stage_kdamonds

def wops_for_target(target, target_has_pid):
    wops = []
    if target_has_pid:
        wops.append({debugfs_target_ids: '%s' % target.pid})
        tid = target.pid
    else:
        if not feature_supported('paddr'):
            raise Exception('paddr is not supported')
        wops.append({debugfs_target_ids: 'paddr\n'})
        tid = 42
    if feature_supported('init_regions_target_idx'):
        tid = 0

    if feature_supported('init_regions'):
        string = ' '.join(['%s %d %d' % (tid, r.start, r.end) for r in
            target.regions])
        wops.append({debugfs_init_regions: string})
    return wops

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

def damos_to_debugfs_input(damos, intervals, scheme_version):
    pattern = damos.access_pattern.converted_for_units(
            _damon.unit_samples, _damon.unit_aggr_intervals,
            intervals)
    quotas = damos.quotas
    watermarks = damos.watermarks

    max_nr_accesses = intervals.aggr / intervals.sample
    v0_scheme = '%d\t%d\t%d\t%d\t%d\t%d\t%d' % (
            pattern.sz_bytes[0], pattern.sz_bytes[1],
            pattern.nr_acc_min_max[0].samples,
            pattern.nr_acc_min_max[1].samples,
            pattern.age_min_max[0].aggr_intervals,
            pattern.age_min_max[1].aggr_intervals,
            damos_action_to_file_input(damos.action))
    if scheme_version == 0:
        return v0_scheme

    v4_scheme = '%s\t' % v0_scheme + '\t'.join(
            '%d' % x for x in [
                # quotas
                quotas.time_ms, quotas.sz_bytes, quotas.reset_interval_ms,
                quotas.weight_sz_permil, quotas.weight_nr_accesses_permil,
                quotas.weight_age_permil,
                # wmarks
                damos_wmarks_metric_to_file_input(watermarks.metric),
                watermarks.interval_us, watermarks.high_permil,
                watermarks.mid_permil, watermarks.low_permil])
    if scheme_version == 4:
        return v4_scheme

    raise Exception('Unsupported scheme version: %d' % scheme_version)

def get_scheme_version():
    '''Return the scheme version that the running kernel supports'''
    scheme_version = 0      # 5.15-based DAMON implementation
    if feature_supported('schemes_speed_limit'):
        scheme_version = 1  # Non-mainlined implementation (deprecated)
    if feature_supported('schemes_prioritization'):
        scheme_version = 2  # Non-mainlined implementation (deprecated)
    if feature_supported('schemes_wmarks'):
        scheme_version = 3  # Non-mainlined implementation (deprecated)
    if feature_supported('schemes_quotas'):
        scheme_version = 4  # 5.16-based DAMON implementation
    return scheme_version

def wops_for_schemes(schemes, intervals):
    scheme_file_input_lines = []
    for scheme in schemes:
        scheme_file_input_lines.append(damos_to_debugfs_input(scheme,
            intervals, get_scheme_version()))
    scheme_file_input = '\n'.join(scheme_file_input_lines)
    if scheme_file_input == '':
        scheme_file_input = '\n'
    return [{debugfs_schemes: scheme_file_input}]

def attr_str_ctx(damon_ctx):
    intervals = damon_ctx.intervals
    nr_regions = damon_ctx.nr_regions
    return '%d %d %d %d %d ' % (intervals.sample, intervals.aggr,
            intervals.ops_update, nr_regions.minimum, nr_regions.maximum)

def wops_for_kdamonds(kdamonds):
    if len(kdamonds) > 1:
        raise Exception('Currently only <=one kdamond is supported')
    if len(kdamonds) == 1 and len(kdamonds[0].contexts) > 1:
        raise Exception('currently only <= one damon_ctx is supported')
    if (len(kdamonds) == 1 and len(kdamonds[0].contexts) == 1 and
            len(kdamonds[0].contexts[0].targets) > 1):
        raise Exception('currently only <= one target is supported')
    ctx = kdamonds[0].contexts[0]

    write_contents = []
    write_contents.append({debugfs_attrs: attr_str_ctx(ctx)})

    if len(ctx.targets) > 0:
        write_contents += wops_for_target(ctx.targets[0],
                _damon.target_has_pid(ctx.ops))

    if not feature_supported('schemes'):
        return write_contents

    write_contents += wops_for_schemes(ctx.schemes, ctx.intervals)

    return write_contents

def stage_kdamonds(kdamonds):
    '''Return error'''
    try:
        wops = wops_for_kdamonds(kdamonds)
    except Exception as e:
        return 'staging kdamond failed (%s)' % e
    return _damo_fs.write_files(wops)

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
    attrs = [int(x) for x in files_content['attrs'].strip().split()]

    intervals = _damon.DamonIntervals(attrs[0], attrs[1], attrs[2])
    nr_regions = _damon.DamonNrRegionsRange(attrs[3], attrs[4])

    target_ids = [int(x) for x in files_content['target_ids'].strip().split()]
    regions_dict = {}
    if feature_supported('init_regions'):
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
    state = files_content['monitor_on'].strip()
    pid = files_content['kdamond_pid'].strip()
    return [_damon.Kdamond(state, pid, [ctx])]

def current_kdamonds():
    return files_content_to_kdamonds(
            _damo_fs.read_files(debugfs_damon))

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

def test_debugfs_file_schemes(nr_fields):
    input_str = ' '.join(['1'] * nr_fields)
    expected = '%s 0 0\n' % input_str

    return test_debugfs_file(debugfs_schemes, input_str, expected)

def test_debugfs_file_schemes_stat_extended(nr_fields):
    input_str = ' '.join(['1'] * nr_fields)
    expected = '%s 0 0 0 0 0\n' % input_str

    return test_debugfs_file(debugfs_schemes, input_str, expected)

def test_init_regions_version(paddr_supported):
    # Save previous values
    orig_target_ids, err = read_value_for_restore(debugfs_target_ids)
    if err != None:
        raise Exception('debugfs target_ids read failed')
    orig_init_regions, err = read_value_for_restore(debugfs_init_regions)
    if err != None:
        raise Exception('debugfs init_regions read failed')

    # Test
    if paddr_supported:
        err = _damo_fs.write_file(debugfs_target_ids, 'paddr\n')
        if err != None:
            raise Exception(err)
        v1_input = '42 100 200'
    else:
        err = _damo_fs.write_file(debugfs_target_ids, '%d\n' % os.getpid())
        if err != None:
            raise Exception(err)
        v1_input = '%d 100 200' % os.getpid()

    # We check if the write was success below anyway, so ignore error
    err = _damo_fs.write_file(debugfs_init_regions, v1_input)
    read_val, err = _damo_fs.read_file(debugfs_init_regions)
    if err != None:
        raise Exception(err)
    if read_val.strip() == v1_input:
        version = 1
    else:
        version = 2

    # Previous value might be invalid now (e.g., process terminated), so ignore
    # error
    err = _damo_fs.write_file(debugfs_target_ids, orig_target_ids)
    err = _damo_fs.write_file(debugfs_init_regions, orig_init_regions)

    return version

def update_supported_features():
    global feature_supports
    if feature_supports != None:
        return None
    feature_supports = {x: False for x in _damon.features}

    if not os.path.isdir(debugfs_damon):
        return 'damon debugfs dir (%s) not found' % debugfs_damon

    if _damon.any_kdamond_running():
        return 'debugfs feature update cannot be done while DAMON running'

    if os.path.isfile(debugfs_schemes):
        feature_supports['schemes'] = True

    # virtual address space has supported since the beginning
    feature_supports['vaddr'] = True
    if test_debugfs_file(debugfs_target_ids, 'paddr\n', '42\n'):
        feature_supports['paddr'] = True

    if os.path.isfile(debugfs_init_regions):
        feature_supports['init_regions'] = True
        init_regions_version = test_init_regions_version(
                feature_supports['paddr'])
        if init_regions_version == 2:
            feature_supports['init_regions_target_idx'] = True

    if feature_supported('schemes'):
        if test_debugfs_file_schemes(9):
            feature_supports['schemes_speed_limit'] = True
        elif test_debugfs_file_schemes(12):
            feature_supports['schemes_speed_limit'] = True
            feature_supports['schemes_prioritization'] = True
        elif test_debugfs_file_schemes(17):
            feature_supports['schemes_speed_limit'] = True
            feature_supports['schemes_prioritization'] = True
            feature_supports['schemes_wmarks'] = True
        elif test_debugfs_file_schemes(18):
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

    if 0 < get_scheme_version() and get_scheme_version() < 4:
        _damo_deprecation_notice.deprecated(
                feature='support of non-mainlined DAMOS implementation',
                deadline='2023-Q2', do_exit=True)

    return None
