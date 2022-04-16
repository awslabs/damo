#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Validate a given damo-record result file"

import argparse
import os

import _damon_result

def assert_value_in_range(value, min_max, name, error_allowed):
    '''Returns 0 if the value is in the range, 1 if the value is out of range
    but error allowed, exit with non-zero else'''
    if not min_max:
        return 0
    if min_max[0] <= value and value <= min_max[1]:
        return 0
    if error_allowed:
        return 1
    print('invalid: expecte %d<=%s<=%d but %d' %
            (min_max[0], name, min_max[1], value))
    exit(1)

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--aggr', metavar='<microseconds>', type=int, nargs=2,
            default=[80000, 120000],
            help='min/max valid sample intervals (us)')
    parser.add_argument('--nr_regions', metavar='<number of regions>',
            type=int, nargs=2, default=[3, 1200],
            help='min/max number of regions')
    parser.add_argument('--nr_accesses', metavar='<number of accesses>',
            type=int, nargs=2, default=[0, 24],
            help='min/max number of measured accesses per aggregate interval')
    parser.add_argument('--allow_error', metavar='<percent>', default=2,
            help='allowed percent of error samples')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if not os.path.isfile(args.input):
        print('the file (%s) not found' % args.input)
        exit(1)

    result = _damon_result.parse_damon_result(args.input, None)
    if not result:
        print('invalid')
        exit(1)

    if len(result.target_snapshots) == 0:
        print('target snapshots is zero')
        exit(1)

    for target in result.target_snapshots:
        nr_snapshots = len(result.target_snapshots[target])
        nr_allowed_errors = nr_snapshots * args.allow_error / 100.0
        nr_aggr_interval_erros = 0
        nr_nr_regions_erros = 0
        for snapshot in result.target_snapshots[target]:
            aggr_interval_us = (snapshot.end_time - snapshot.start_time) / 1000
            nr_aggr_interval_erros += assert_value_in_range( aggr_interval_us,
                    args.aggr, 'aggregate interval',
                    nr_aggr_interval_erros < nr_allowed_errors)

            nr_nr_regions_erros += assert_value_in_range(len(snapshot.regions),
                    args.nr_regions, 'nr_regions',
                    nr_nr_regions_erros < nr_allowed_errors)

            for region in snapshot.regions:
                if region.start >= region.end:
                    print('wrong regiosn [%d, %d)' % (saddr, eaddr))
                    exit(1)

                assert_value_in_range(region.nr_accesses, args.nr_accesses,
                        'nr_accesses', False)

if __name__ == '__main__':
    main()
