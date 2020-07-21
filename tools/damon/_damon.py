#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON debugfs control.
"""

import os
import subprocess

debugfs_attrs = None
debugfs_record = None
debugfs_schemes = None
debugfs_target_ids = None
debugfs_init_regions = None
debugfs_monitor_on = None

def set_target_id(tid):
    with open(debugfs_target_ids, 'w') as f:
        f.write('%s\n' % tid)

def set_target(tid, init_regions=[]):
    rc = set_target_id(tid)
    if rc:
        return rc

    if not os.path.exists(debugfs_init_regions):
        return 0

    if tid == 'paddr':
        tid = 42
    string = ' '.join(['%s %d %d' % (tid, r[0], r[1]) for r in init_regions])
    return subprocess.call('echo "%s" > %s' % (string, debugfs_init_regions),
            shell=True, executable='/bin/bash')

def turn_damon(on_off):
    return subprocess.call("echo %s > %s" % (on_off, debugfs_monitor_on),
            shell=True, executable="/bin/bash")

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
        return "%s %s %s %s %s %s %s\n%s" % (self.sample_interval,
                self.aggr_interval, self.regions_update_interval,
                self.min_nr_regions, self.max_nr_regions, self.rbuf_len,
                self.rfile_path, self.schemes)

    def attr_str(self):
        return "%s %s %s %s %s " % (self.sample_interval, self.aggr_interval,
                self.regions_update_interval, self.min_nr_regions,
                self.max_nr_regions)

    def record_str(self):
        return '%s %s ' % (self.rbuf_len, self.rfile_path)

    def apply(self):
        ret = subprocess.call('echo %s > %s' % (self.attr_str(), debugfs_attrs),
                shell=True, executable='/bin/bash')
        if ret:
            return ret
        ret = subprocess.call('echo %s > %s' % (self.record_str(),
            debugfs_record), shell=True, executable='/bin/bash')
        if ret:
            return ret
        return subprocess.call('echo %s > %s' % (
            self.schemes.replace('\n', ' '), debugfs_schemes), shell=True,
            executable='/bin/bash')

def current_attrs():
    with open(debugfs_attrs, 'r') as f:
        attrs = f.read().split()
    attrs = [int(x) for x in attrs]

    with open(debugfs_record, 'r') as f:
        rattrs = f.read().split()
    attrs.append(int(rattrs[0]))
    attrs.append(rattrs[1])

    with open(debugfs_schemes, 'r') as f:
        schemes = f.read()

    # The last two fields in each line are statistics.  Remove those.
    schemes = [' '.join(x.split()[:-2]) for x in schemes.strip().split('\n')]
    attrs.append('\n'.join(schemes))

    return Attrs(*attrs)

def chk_update_debugfs(debugfs):
    global debugfs_attrs
    global debugfs_record
    global debugfs_schemes
    global debugfs_target_ids
    global debugfs_init_regions
    global debugfs_monitor_on

    debugfs_damon = os.path.join(debugfs, 'damon')
    debugfs_attrs = os.path.join(debugfs_damon, 'attrs')
    debugfs_record = os.path.join(debugfs_damon, 'record')
    debugfs_schemes = os.path.join(debugfs_damon, 'schemes')
    debugfs_target_ids = os.path.join(debugfs_damon, 'target_ids')
    debugfs_init_regions = os.path.join(debugfs_damon, 'init_regions')
    debugfs_monitor_on = os.path.join(debugfs_damon, 'monitor_on')

    if not os.path.isdir(debugfs_damon):
        print("damon debugfs dir (%s) not found", debugfs_damon)
        exit(1)

    for f in [debugfs_attrs, debugfs_record, debugfs_schemes,
            debugfs_target_ids, debugfs_monitor_on]:
        if not os.path.isfile(f):
            print("damon debugfs file (%s) not found" % f)
            exit(1)

def cmd_args_to_attrs(args):
    "Generate attributes with specified arguments"
    sample_interval = args.sample
    aggr_interval = args.aggr
    regions_update_interval = args.updr
    min_nr_regions = args.minr
    max_nr_regions = args.maxr
    rbuf_len = args.rbuf
    if not os.path.isabs(args.out):
        args.out = os.path.join(os.getcwd(), args.out)
    rfile_path = args.out
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
            default=5000, help='sampling interval')
    parser.add_argument('-a', '--aggr', metavar='<interval>', type=int,
            default=100000, help='aggregate interval')
    parser.add_argument('-u', '--updr', metavar='<interval>', type=int,
            default=1000000, help='regions update interval')
    parser.add_argument('-n', '--minr', metavar='<# regions>', type=int,
            default=10, help='minimal number of regions')
    parser.add_argument('-m', '--maxr', metavar='<# regions>', type=int,
            default=1000, help='maximum number of regions')

def set_init_regions_argparser(parser):
    parser.add_argument('-r', '--regions', metavar='"<start>-<end> ..."',
            type=str, default='', help='monitoring target address regions')
