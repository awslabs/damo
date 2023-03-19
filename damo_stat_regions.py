#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse

import damo_stat

import _damo_fmt_str
import _damo_subcmds
import _damon
import _damon_result

def priority(region, weights):
    if region.nr_accesses > 0:
        return region.nr_accesses * weights[0] + region.age * weights[1]
    return region.age * weights[1] * -1

def __pr_schemes_tried_regions(regions, intervals, size_only, sortby,
        prio_weights, raw_nr):

    if sortby == 'priority':
        regions.sort(key=lambda region: priority(region, prio_weights))

    total_sz = 0
    for region in regions:
        region = _damon.DamosTriedRegion(region.start, region.end,
                region.nr_accesses, region.age)
        if not size_only:
            print(region.to_str(raw_nr, intervals))
        else:
            total_sz += (region.end - region.start)
    if size_only:
        print('%s' % _damo_fmt_str.format_sz(total_sz, raw_nr))

def update_pr_schemes_tried_regions(access_pattern, size_only, sortby,
        prio_weights, raw_nr):
    snapshots, err = _damon_result.get_snapshots(access_pattern)
    if snapshots == None:
        print(err)
        return

    for kdamond, ctx_snapshots in snapshots.items():
        for ctx, snapshot in ctx_snapshots.items():
            print('kdamond %s ctx %s' % (kdamond.name, ctx.name))
            __pr_schemes_tried_regions(snapshot.regions, ctx.intervals,
                    size_only, sortby, prio_weights, raw_nr)

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
    parser.add_argument('--sortby', choices=['address', 'priority'],
            default='sortby',
            help='the metric for the regions print order')
    parser.add_argument('--priority_weights', nargs=2, type=float,
            default=[1, 1,],
            metavar=('<access rate weight>, <age weight>'),
            help='priority weights for priority calculation')

def __main(args):
    update_pr_schemes_tried_regions(args.access_pattern, args.size_only,
            args.sortby, args.priority_weights, args.raw)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    args.access_pattern = _damon.DamosAccessPattern(args.sz_region,
            args.access_rate, _damon.unit_percent, args.age, _damon.unit_usec)

    damo_stat.run_count_delay(__main, args)

if __name__ == '__main__':
    main()
