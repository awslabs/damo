#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Validate a given damo-record result file"

import argparse

import _damon_result

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--aggr', metavar='<interval>', type=int, nargs=2,
            help='min/max valid sample intervals (ns)')
    parser.add_argument('--nr_regions', metavar='<number>', type=int, nargs=2,
            help='min/max number of regions')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    result = _damon_result.parse_damon_result(args.input, None)
    if not result:
        print('invalid')
        exit(1)

    for target in result.target_snapshots:
        for snapshot in result.target_snapshots[target]:
            aggr_int_ns = snapshot.end_time - snapshot.start_time
            if args.aggr and (aggr_int_ns < args.aggr[0] or
                    aggr_int_ns > args.aggr[1]):
                print('invalid: expected %d<=aggregate interval<=%d, but %d' %
                        (args.aggr[0], args.aggr[1], aggr_int_ns))
                exit(1)

            nr_regions = len(snapshot.regions)
            if args.nr_regions and (nr_regions < args.nr_regions[0] or
                    nr_regions > args.nr_regions[1]):
                print('invalid: expected %d<=nr_regions<=%d, but %d' %
                        (args.nr_regions[0], args.nr_regions[1], nr_regions))
                exit(1)

    print('valid')

if __name__ == '__main__':
    main()
