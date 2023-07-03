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
    print('invalid: expect %d<=%s<=%d but %d' %
            (min_max[0], name, min_max[1], value))
    exit(1)

def check_boundary(region, regions_boundary):
    in_boundary = False
    for boundary in regions_boundary:
        if (region.start >= boundary[0] and
                region.end <= boundary[1]):
            in_boundary = True
            break
    if not in_boundary:
        print('region %s-%s out of the boundary' %
                (region.start, region.end))
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
    parser.add_argument('--regions_boundary', metavar='<start>-<end>',
            nargs='+', help='regions boundary')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if not os.path.isfile(args.input):
        print('the file (%s) not found' % args.input)
        exit(1)

    regions_boundary = []
    if args.regions_boundary:
        for boundary in args.regions_boundary:
            parsed_boundary = [int(x) for x in boundary.split('-')]
            if not len(parsed_boundary) == 2:
                print('wrong boundary input %s' % boundary)
            regions_boundary.append(parsed_boundary)

    records, err = _damon_result.parse_records_file(args.input)
    if err != None:
        print('parsing failed (%s)' % err)
        exit(1)

    if len(records) == 0:
        print('target snapshots is zero')
        exit(1)

    for record in records:
        target = record.target_id
        nr_snapshots = len(record.snapshots)
        nr_allowed_errors = nr_snapshots * args.allow_error / 100.0
        nr_aggr_interval_errors = 0
        nr_nr_regions_erros = 0
        for snapshot in record.snapshots:
            aggr_interval_us = (snapshot.end_time - snapshot.start_time) / 1000
            nr_aggr_interval_errors += assert_value_in_range( aggr_interval_us,
                    args.aggr, 'aggregate interval',
                    nr_aggr_interval_errors < nr_allowed_errors)

            nr_nr_regions_erros += assert_value_in_range(len(snapshot.regions),
                    args.nr_regions, 'nr_regions',
                    nr_nr_regions_erros < nr_allowed_errors)

            for region in snapshot.regions:
                if region.start >= region.end:
                    print('wrong regiosn [%d, %d)' % (saddr, eaddr))
                    exit(1)

                if regions_boundary:
                    check_boundary(region, regions_boundary)

                assert_value_in_range(region.nr_accesses.samples,
                        args.nr_accesses, 'nr_accesses', False)

if __name__ == '__main__':
    main()
