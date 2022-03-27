#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON debugfs control.
"""

import os
import subprocess

import _damon

debugfs_damon = None
debugfs_version = None
debugfs_attrs = None
debugfs_record = None
debugfs_schemes = None
debugfs_target_ids = None
debugfs_init_regions = None
debugfs_monitor_on = None

def set_target_id(tid):
    try:
        with open(debugfs_target_ids, 'w') as f:
            f.write('%s\n' % tid)
    except Exception as e:
        return e

def set_target(tid, init_regions=[]):
    rc = set_target_id(tid)
    if rc:
        return rc

    if not debugfs_init_regions:
        return 0

    if feature_supported('init_regions_target_idx'):
        tid = 0
    elif tid == 'paddr':
        tid = 42

    string = ' '.join(['%s %d %d' % (tid, r[0], r[1]) for r in init_regions])
    return subprocess.call('echo "%s" > %s' % (string, debugfs_init_regions),
            shell=True, executable='/bin/bash')

def turn_damon(on_off):
    return subprocess.call('echo %s > %s' % (on_off, debugfs_monitor_on),
            shell=True, executable='/bin/bash')

def is_damon_running():
    with open(debugfs_monitor_on, 'r') as f:
        return f.read().strip() == 'on'

def current_attrs():
    with open(debugfs_attrs, 'r') as f:
        attrs = f.read().split()
    attrs = [int(x) for x in attrs]

    if debugfs_record:
        with open(debugfs_record, 'r') as f:
            rattrs = f.read().split()
        attrs.append(int(rattrs[0]))
        attrs.append(rattrs[1])
    else:
        attrs += [None, None]

    if debugfs_schemes:
        with open(debugfs_schemes, 'r') as f:
            schemes = f.read()
        # The last two fields in each line are statistics.  Remove those.
        schemes = [' '.join(x.split()[:-2]) for x in schemes.strip().split('\n')]
        attrs.append('\n'.join(schemes))
    else:
        attrs.append(None)

    return _damon.Attrs(*attrs)

feature_supports = None

def feature_supported(feature):
    if feature_supports == None:
        initialize()

    return feature_supports[feature]

def get_supported_features():
    if feature_supports == None:
        initialize()
    return feature_supports

def test_debugfs_file(path, input_str, expected):
    passed = False
    with open(path, 'r') as f:
        orig_value = f.read()
        if orig_value == '':
            orig_value = '\n'
    if os.path.basename(path) == 'target_ids' and orig_value == '42\n':
        orig_value = 'paddr\n'
    try:
        with open(path, 'w') as f:
            f.write(input_str)
        with open(path, 'r') as f:
            if f.read() == expected:
                passed = True
    except Exception as e:
        passed = False
    with open(path, 'w') as f:
        f.write(orig_value)
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
    with open(debugfs_target_ids, 'r') as f:
        orig_target_ids = f.read()
        if orig_target_ids == '':
            orig_target_ids = '\n'
        if orig_target_ids == '42\n':
            orig_target_ids = 'paddr\n'
    with open(debugfs_init_regions, 'r') as f:
        orig_init_regions = f.read()
        if orig_init_regions == '':
            orig_init_regions = '\n'

    # Test
    with open(debugfs_target_ids, 'w') as f:
        if paddr_supported:
            f.write('paddr\n')
        else:
            f.write('%d\n' % os.getpid())

    if paddr_supported:
        v1_input = '42 100 200'
    else:
        v1_input = '%d 100 200' % os.getpid()
    try:
        with open(debugfs_init_regions, 'w') as f:
            f.write(v1_input)
    except IOError as e:
        version = 2
    with open(debugfs_init_regions, 'r') as f:
        if f.read().strip() == v1_input:
            version = 1
        else:
            version = 2

    # Restore previous values
    try:
        with open(debugfs_target_ids, 'w') as f:
            f.write(orig_target_ids)
        with open(debugfs_init_regions, 'w') as f:
            f.write(orig_init_regions)
    except IOError:
        # Previous value might be invalid now (e.g., process terminated)
        pass
    return version

def update_supported_features():
    global feature_supports
    if feature_supports != None:
        return None
    feature_supports = {x: False for x in _damon.features}

    err = kernel_issue()
    if err != None:
        return err

    if debugfs_record != None:
        feature_supports['record'] = True
    if debugfs_schemes != None:
        feature_supports['schemes'] = True

    if test_debugfs_file(debugfs_target_ids, 'paddr\n', '42\n'):
        feature_supports['paddr'] = True

    if debugfs_init_regions != None:
        feature_supports['init_regions'] = True
        init_regions_version = test_init_regions_version(
                feature_supports['paddr'])
        if init_regions_version == 2:
            feature_supports['init_regions_target_idx'] = True

    if debugfs_schemes != None:
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
    return None

def kernel_issue():
    'Return a problem in kernel for using DAMON debugfs interface'
    global debugfs_damon
    global debugfs_version
    global debugfs_attrs
    global debugfs_record
    global debugfs_schemes
    global debugfs_target_ids
    global debugfs_init_regions
    global debugfs_monitor_on

    if not os.path.isdir(debugfs_damon):
        return 'damon debugfs dir (%s) not found' % debugfs_damon

    for f in [debugfs_version, debugfs_attrs, debugfs_record, debugfs_schemes,
            debugfs_target_ids, debugfs_init_regions, debugfs_monitor_on]:
        # f could be None if this function is called before
        if f == None:
            continue
        if not os.path.isfile(f):
            if f == debugfs_version:
                debugfs_version = None
            elif f == debugfs_record:
                debugfs_record = None
            elif f == debugfs_schemes:
                debugfs_schemes = None
            elif f == debugfs_init_regions:
                debugfs_init_regions = None
            else:
                return 'damon debugfs file (%s) not found' % f
    return None

def set_root(root):
    global debugfs_damon
    global debugfs_version
    global debugfs_attrs
    global debugfs_record
    global debugfs_schemes
    global debugfs_target_ids
    global debugfs_init_regions
    global debugfs_monitor_on

    debugfs = root
    debugfs_damon = os.path.join(debugfs, 'damon')
    debugfs_version = os.path.join(debugfs_damon, 'version')
    debugfs_attrs = os.path.join(debugfs_damon, 'attrs')
    debugfs_record = os.path.join(debugfs_damon, 'record')
    debugfs_schemes = os.path.join(debugfs_damon, 'schemes')
    debugfs_target_ids = os.path.join(debugfs_damon, 'target_ids')
    debugfs_init_regions = os.path.join(debugfs_damon, 'init_regions')
    debugfs_monitor_on = os.path.join(debugfs_damon, 'monitor_on')

def initialize(args, skip_dirs_population=False):
    set_root(args.debugfs)
    err = update_supported_features()
    if err:
        return err
    return None

def attr_str(attrs):
    return '%s %s %s %s %s ' % (attrs.sample_interval, attrs.aggr_interval,
            attrs.regions_update_interval, attrs.min_nr_regions,
            attrs.max_nr_regions)

def record_str(attrs):
    return '%s %s ' % (attrs.rbuf_len, attrs.rfile_path)

def attrs_apply(attrs):
    ret = subprocess.call('echo %s > %s' % (attr_str(attrs), debugfs_attrs),
            shell=True, executable='/bin/bash')
    if ret:
        return ret
    if debugfs_record:
        ret = subprocess.call('echo %s > %s' % (record_str(attrs),
            debugfs_record), shell=True, executable='/bin/bash')
        if ret:
            return ret
    if not debugfs_schemes:
        return 0
    return subprocess.call('echo %s > %s' % (
        attrs.schemes.replace('\n', ' '), debugfs_schemes), shell=True,
        executable='/bin/bash')
