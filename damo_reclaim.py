# SPDX-License-Identifier: GPL-2.0

"Control DAMON_RECLAIM"

import argparse
import os
import time

import _damon

darc_params_dir = '/sys/module/damon_reclaim/parameters'
# parameters that existed since the initial release of DAMON_RECLAIM
darc_essential_params = ['kdamond_pid', 'enabled', 'min_age', 'quota_ms',
        'quota_sz', 'quota_reset_interval_ms', 'wmarks_interval',
        'wmarks_high', 'wmarks_mid', 'wmarks_low', 'sample_interval',
        'aggr_interval', 'min_nr_regions', 'max_nr_regions',
        'monitor_region_start', 'monitor_region_end']

# parameters that introduced after the initial release
darc_optional_params = ['nr_reclaim_tried_regions', 'nr_reclaimed_regions',
        'bytes_reclaim_tried_regions', 'bytes_reclaimed_regions']

def chk_darc_sysfs():
    if not os.path.isdir(darc_params_dir):
        print('%s not found' % darc_params_dir)
    for param in darc_essential_params:
        param_file = os.path.join(darc_params_dir, param)
        if not os.path.isfile(param_file):
            print('%s file not found' % param_file)
            exit(1)

def set_param(param, val):
    if val == None:
        return
    path = os.path.join(darc_params_dir, param)
    with open(path, 'w') as f:
        f.write('%s' % val)

def darc_running():
    with open(os.path.join(darc_params_dir, 'kdamond_pid')) as f:
        return f.read() != '-1\n'

def darc_enable(on):
    if not on:
        set_param('enabled', 'N')
        while darc_running():
            time.sleep(1)
        return

    set_param('enabled', 'N')
    while darc_running():
        time.sleep(1)
    set_param('enabled', 'Y')
    while not darc_running():
        time.sleep(1)
    return

def darc_read_status():
    for param in darc_essential_params + darc_optional_params:
        param_file = os.path.join(darc_params_dir, param)
        if not os.path.isfile(param_file):
            continue

        with open(param_file, 'r') as f:
            print('%s: %s' % (param, f.read().strip()))

def set_argparser(parser):
    parser.add_argument('action', type=str, nargs='?',
            choices=['status', 'enable', 'disable'], default='status',
            help='read status, enable, or disable DAMON_RECLAIM')
    parser.add_argument('--min_age', type=int, metavar='<microseconds>',
            help='time threshold for cold memory regions identification (us)')
    parser.add_argument('--quota', type=int,
            metavar=('<ms>', '<bytes>', '<ms>'), nargs=3,
            default=[None] * 3,
            help='quotas for time and size, and reset interval')
    parser.add_argument('--wmarks', type=int,
            metavar=('<us>', '<per-thousand>', '<per-thousand>',
                '<per-thousand>'),
            nargs=4, default=[None] * 4,
            help='watermarks check interval and three watermarks')
    parser.add_argument('--monitor_intervals', type=int,
            metavar='<microseconds>', nargs=2, default=[None] * 2,
            help='intervals for sampling and aggregation of DAMON')
    parser.add_argument('--nr_regions', type=int, metavar='<number>',
            nargs=2, default=[None] * 2,
            help='minimum and maximum number of DAMON memory regions')
    parser.add_argument('--monitor_region', type=int, metavar='<phy addr>',
            nargs=2, default=[None] * 2,
            help='start and end addresses of the target memory region')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    chk_darc_sysfs()

    if args.action == 'status':
        darc_read_status()
        return

    set_param('min_age', args.min_age)
    set_param('quota_ms', args.quota[0])
    set_param('quota_sz', args.quota[1])
    set_param('quota_reset_interval_ms', args.quota[2])
    set_param('wmarks_interval', args.wmarks[0])
    set_param('wmarks_high', args.wmarks[1])
    set_param('wmarks_mid', args.wmarks[2])
    set_param('wmarks_low', args.wmarks[3])
    set_param('sample_interval', args.monitor_intervals[0])
    set_param('aggr_interval', args.monitor_intervals[1])
    set_param('min_nr_regions', args.nr_regions[0])
    set_param('max_nr_regions', args.nr_regions[1])
    set_param('monitor_region_start', args.monitor_region[0])
    set_param('monitor_region_end', args.monitor_region[1])

    darc_enable(args.action == 'enable')

if __name__ == '__main__':
    main()
