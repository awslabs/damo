#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON debugfs control.
"""

import os
import subprocess

debugfs_version = None
debugfs_attrs = None
debugfs_record = None
debugfs_schemes = None
debugfs_target_ids = None
debugfs_init_regions = None
debugfs_monitor_on = None

def chk_permission():
    if os.geteuid() != 0:
        print('Run as root')
        exit(1)

def set_target_id(tid):
    with open(debugfs_target_ids, 'w') as f:
        f.write('%s\n' % tid)

def set_target(tid, init_regions=[]):
    rc = set_target_id(tid)
    if rc:
        return rc

    if not debugfs_init_regions:
        return 0

    if tid == 'paddr':
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

class Attrs:
    sample_interval = None
    aggr_interval = None
    regions_update_interval = None
    min_nr_regions = None
    max_nr_regions = None
    rbuf_len = None
    rfile_path = None
    schemes = None

    def __init__(self, s, a, r, n, x, l, f, c):
        self.sample_interval = s
        self.aggr_interval = a
        self.regions_update_interval = r
        self.min_nr_regions = n
        self.max_nr_regions = x
        self.rbuf_len = l
        self.rfile_path = f
        self.schemes = c

    def __str__(self):
        return '%s %s %s %s %s %s %s\n%s' % (self.sample_interval,
                self.aggr_interval, self.regions_update_interval,
                self.min_nr_regions, self.max_nr_regions, self.rbuf_len,
                self.rfile_path, self.schemes)

    def attr_str(self):
        return '%s %s %s %s %s ' % (self.sample_interval, self.aggr_interval,
                self.regions_update_interval, self.min_nr_regions,
                self.max_nr_regions)

    def record_str(self):
        return '%s %s ' % (self.rbuf_len, self.rfile_path)

    def apply(self):
        ret = subprocess.call('echo %s > %s' % (self.attr_str(), debugfs_attrs),
                shell=True, executable='/bin/bash')
        if ret:
            return ret
        if debugfs_record:
            ret = subprocess.call('echo %s > %s' % (self.record_str(),
                debugfs_record), shell=True, executable='/bin/bash')
            if ret:
                return ret
        if not debugfs_schemes:
            return 0
        return subprocess.call('echo %s > %s' % (
            self.schemes.replace('\n', ' '), debugfs_schemes), shell=True,
            executable='/bin/bash')

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

    return Attrs(*attrs)

feature_supports = None

def feature_supported(feature):
    if feature_supports == None:
        chk_update_debugfs()

    return feature_supports[feature]

def get_supported_features():
    if feature_supports == None:
        chk_update_debugfs()
    return feature_supports

def test_debugfs_file(path, input_str, expected):
    passed = False
    with open(path, 'r') as f:
        orig_value = f.read()
        if orig_value == '':
            orig_value = '\n'
    if os.path.basename(path) == 'target_ids' and orig_value == '42\n':
        orig_value = 'paddr\n'
    with open(path, 'w') as f:
        f.write(input_str)
    with open(path, 'r') as f:
        if f.read() == expected:
            passed = True
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

def update_supported_features():
    if debugfs_record != None:
        feature_supports['record'] = True
    if debugfs_schemes != None:
        feature_supports['schemes'] = True
    if debugfs_init_regions != None:
        feature_supports['init_regions'] = True

    if test_debugfs_file(debugfs_target_ids, 'paddr\n', '42\n'):
        feature_supports['paddr'] = True

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

def chk_update_debugfs(debugfs='/sys/kernel/debug/'):
    global feature_supports
    global debugfs_version
    global debugfs_attrs
    global debugfs_record
    global debugfs_schemes
    global debugfs_target_ids
    global debugfs_init_regions
    global debugfs_monitor_on

    if feature_supports != None:
        return
    feature_supports = {
            'record': False,
            'schemes': False,
            'init_regions': False,
            'paddr': False,
            'schemes_speed_limit': False,
            'schemes_quotas': False,
            'schemes_prioritization': False,
            'schemes_wmarks': False,
            }

    debugfs_damon = os.path.join(debugfs, 'damon')
    debugfs_version = os.path.join(debugfs_damon, 'version')
    debugfs_attrs = os.path.join(debugfs_damon, 'attrs')
    debugfs_record = os.path.join(debugfs_damon, 'record')
    debugfs_schemes = os.path.join(debugfs_damon, 'schemes')
    debugfs_target_ids = os.path.join(debugfs_damon, 'target_ids')
    debugfs_init_regions = os.path.join(debugfs_damon, 'init_regions')
    debugfs_monitor_on = os.path.join(debugfs_damon, 'monitor_on')

    if not os.path.isdir(debugfs_damon):
        print('damon debugfs dir (%s) not found' % debugfs_damon)
        exit(1)

    for f in [debugfs_version, debugfs_attrs, debugfs_record, debugfs_schemes,
            debugfs_target_ids, debugfs_init_regions, debugfs_monitor_on]:
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
                print('damon debugfs file (%s) not found' % f)
                exit(1)

    update_supported_features()

def cmd_args_to_attrs(args):
    'Generate attributes with specified arguments'
    sample_interval = args.sample
    aggr_interval = args.aggr
    regions_update_interval = args.updr
    min_nr_regions = args.minr
    max_nr_regions = args.maxr
    rbuf_len = args.rbuf
    if not os.path.isabs(args.out):
        args.out = os.path.join(os.getcwd(), args.out)
    rfile_path = args.out

    if not hasattr(args, 'schemes'):
        args.schemes = ''
    schemes = args.schemes

    return Attrs(sample_interval, aggr_interval, regions_update_interval,
            min_nr_regions, max_nr_regions, rbuf_len, rfile_path, schemes)

def cmd_args_to_init_regions(args):
    regions = []
    for arg in args.regions.split():
        addrs = arg.split('-')
        try:
            if len(addrs) != 2:
                raise Exception('two addresses not given')
            start = int(addrs[0])
            end = int(addrs[1])
            if start >= end:
                raise Exception('start >= end')
            if regions and regions[-1][1] > start:
                raise Exception('regions overlap')
        except Exception as e:
            print('Wrong \'--regions\' argument (%s)' % e)
            exit(1)

        regions.append([start, end])
    return regions

def set_attrs_argparser(parser):
    parser.add_argument('-d', '--debugfs', metavar='<debugfs>', type=str,
            default='/sys/kernel/debug', help='debugfs mounted path')
    parser.add_argument('-s', '--sample', metavar='<interval>', type=int,
            default=5000, help='sampling interval (us)')
    parser.add_argument('-a', '--aggr', metavar='<interval>', type=int,
            default=100000, help='aggregate interval (us)')
    parser.add_argument('-u', '--updr', metavar='<interval>', type=int,
            default=1000000, help='regions update interval (us)')
    parser.add_argument('-n', '--minr', metavar='<# regions>', type=int,
            default=10, help='minimal number of regions')
    parser.add_argument('-m', '--maxr', metavar='<# regions>', type=int,
            default=1000, help='maximum number of regions')

def set_init_regions_argparser(parser):
    parser.add_argument('-r', '--regions', metavar='"<start>-<end> ..."',
            type=str, default='', help='monitoring target address regions')
