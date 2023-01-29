#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_stat

import _damo_fmt_str
import _damo_subcmds
import _damon

def out_of_range(minval, val, maxval):
    return val < minval or maxval < val

def __pr_schemes_tried_regions(regions, intervals, access_pattern, size_only,
        raw_nr):
    access_pattern.convert_for_units(_damon.unit_sample_intervals,
            _damon.unit_aggr_intervals, ctx.intervals)
    total_sz = 0
    for region in regions:
        sz = region.end - region.start
        if out_of_range(access_pattern.min_sz_bytes, sz,
                access_pattern.max_sz_bytes):
            continue
        if out_of_range(access_pattern.min_nr_accesses,
                region.nr_accesses,
                access_pattern.max_nr_accesses):
            continue
        if out_of_range(access_pattern.min_age, region.age,
                access_pattern.max_age):
            continue
        if not size_only:
            print(region.to_str(raw_nr, intervals))
        else:
            total_sz += sz
    if size_only:
        print('%s' % _damo_fmt_str.format_sz(total_sz, raw_nr))

def pr_schemes_tried_regions(kdamond_name, monitoring_scheme,
        access_pattern, size_only, raw_nr):
    for kdamond in _damon.current_kdamonds():
        if kdamond.name != kdamond_name:
            continue
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                if scheme != monitoring_scheme:
                    continue
                __pr_schemes_tried_regions(scheme.tried_regions, ctx.intervals,
                        access_pattern, size_only, raw_nr)
                return

def monitoring_kdamond_scheme():
    monitoring_kdamond = None
    monitoring_scheme = None
    kdamonds = _damon.current_kdamonds()
    for kdamond in kdamonds:
        for ctx in kdamond.contexts:
            for scheme in ctx.schemes:
                if _damon.is_monitoring_scheme(scheme, ctx.intervals):
                    return kdamond.name, scheme
    return None, None

def update_pr_schemes_tried_regions(access_pattern, size_only, raw_nr):
    if _damon.every_kdamond_turned_off():
        print('no kdamond running')
        return

    monitoring_kdamond, monitoring_scheme = monitoring_kdamond_scheme()
    if monitoring_kdamond == None:
        print('no kdamond is having monitoring scheme')
        return

    err = _damon.update_schemes_tried_regions([monitoring_kdamond])
    if err != None:
        print('update schemes tried regions fail: %s', err)
        return

    pr_schemes_tried_regions(monitoring_kdamond, monitoring_scheme,
            access_pattern, size_only, raw_nr)

def set_argparser(parser):
    damo_stat.set_common_argparser(parser)
    parser.add_argument('--sz_region', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max size of regions (bytes)')
    parser.add_argument('--access_rate', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max access rate of regions (percent)')
    parser.add_argument('--age', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max age of regions (microseconds)')
    parser.add_argument('--size_only', action='store_true',
            help='print total size only')

def __main(args):
    update_pr_schemes_tried_regions(args.damo_stat_regions_access_pattern,
            args.size_only, args.raw)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    args.damo_stat_regions_access_pattern = _damon.DamosAccessPattern(
            args.sz_region, args.access_rate, _damon.unit_percent, args.age,
            _damon.unit_usec)

    damo_stat.run_count_delay(__main, args)

    for i in range(args.count):
        if i != args.count - 1:
            time.sleep(args.delay)

if __name__ == '__main__':
    main()
