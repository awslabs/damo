#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Control DAMON_RECLAIM"

import argparse
import os
import time

darc_params_dir = '/sys/module/damon_reclaim/parameters'
darc_params = ['enabled', 'min_age', 'quota_ms', 'quota_sz',
        'charge_window_ms', 'wmarks_interval', 'wmarks_high', 'wmarks_mid',
        'wmarks_low', 'sample_interval', 'aggr_interval', 'min_nr_regions',
        'max_nr_regions', 'monitor_region_start', 'monitor_region_end',
        'kdamond_pid']

def chk_permission():
    if os.geteuid() != 0:
        print('Run as root')
        exit(1)

def chk_darc_sysfs():
    if not os.path.isdir(darc_params_dir):
        print('%s not found' % darc_params_dir)
    for param in darc_params:
        param_file = os.path.join(darc_params_dir, param)
        if not os.path.isfile(param_file):
            print('%s file not found' % param_file)
            exit(1)

def set_param(param, val):
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

def set_argparser(parser):
    parser.add_argument('enable', type=str, metavar='<mode>', nargs='?',
            choices=['enable', 'disable'], default='enable',
            help='(re-)enable or disable DAMON_RECLAIM')
    parser.add_argument('--min_age', type=int, metavar='<microseconds>',
            default=5000000,
            help='time threshold for cold memory regions identification (us)')
    parser.add_argument('--quota_ms', type=int, metavar='<milliseconds>',
            default=100, help='time limit in milliseconds')
    parser.add_argument('--quota_sz', type=int, metavar='<bytes>',
            default=1024*1024*1024, help='size limit in bytes')
    parser.add_argument('--charge_window_ms', type=int,
            metavar='<milliseconds>', default=1000,
            help='limit charge time window in milliseconds')
    parser.add_argument('--wmarks_interval', type=int,
            metavar='<microseconds>', default=5000000,
            help='watermarks check time interval in microseconds')
    parser.add_argument('--wmarks_high', type=int, metavar='<per-thousand>',
            default=500, help='high watermark in per-thousand')
    parser.add_argument('--wmarks_mid', type=int, metavar='<per-thousand>',
            default=400, help='mid watermark in per-thousand')
    parser.add_argument('--wmarks_low', type=int, metavar='<per-thousand>',
            default=200, help='low watermark in per-thousand')
    parser.add_argument('--sample_interval', type=int,
            metavar='<microseconds>', default=5000,
            help='sampling interval in microseconds')
    parser.add_argument('--aggr_interval', type=int, metavar='<microseconds>',
            default=100000,
            help='aggregation interval in microseconds')
    parser.add_argument('--min_nr_regions', type=int, metavar='<number>',
            default=10, help='minimum number of memory regions')
    parser.add_argument('--max_nr_regions', type=int, metavar='<number>',
            default=1000, help='maximum number of memory regions')
    parser.add_argument('--monitor_region_start', type=int,
            metavar='<phy addr>', default=0,
            help='start address of target memory region')
    parser.add_argument('--monitor_region_end', type=int,
            metavar='<phy addr>', default=0,
            help='end address of target memory region')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    chk_permission()
    chk_darc_sysfs()

    set_param('min_age', args.min_age)
    set_param('quota_ms', args.quota_ms)
    set_param('quota_sz', args.quota_sz)
    set_param('charge_window_ms', args.charge_window_ms)
    set_param('wmarks_interval', args.wmarks_interval)
    set_param('wmarks_high', args.wmarks_high)
    set_param('wmarks_mid', args.wmarks_mid)
    set_param('wmarks_low', args.wmarks_low)
    set_param('sample_interval', args.sample_interval)
    set_param('aggr_interval', args.aggr_interval)
    set_param('min_nr_regions', args.min_nr_regions)
    set_param('max_nr_regions', args.max_nr_regions)
    set_param('monitor_region_start', args.monitor_region_start)
    set_param('monitor_region_end', args.monitor_region_end)

    darc_enable(args.enable == 'enable')

if __name__ == '__main__':
    main()
