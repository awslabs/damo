#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Adjust a damon monitoring result with new attributes"

import argparse
import os
import struct

import _damon_result

def adjusted_snapshots(snapshots, aggregate_interval_us):
    adjusted = []
    to_aggregate = []
    for snapshot in snapshots:
        to_aggregate.append(snapshot)
        interval_ns = to_aggregate[-1].end_time - to_aggregate[0].start_time
        if interval_ns >= aggregate_interval_us * 1000:
            adjusted.append(_damon_result.aggregate_snapshots(to_aggregate))
            to_aggregate = []
    return adjusted

def adjust_result(result, aggregate_interval, nr_snapshots_to_skip):
    for record in result.records:
        record.snapshots = adjusted_snapshots(
                record.snapshots[nr_snapshots_to_skip:], aggregate_interval)

def set_argparser(parser):
    parser.add_argument('--aggregate_interval', type=int, default=None,
            metavar='<microseconds>', help='new aggregation interval')
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--output', '-o', type=str, metavar='<file>',
            default='damon.adjusted.data', help='output file name')
    parser.add_argument('--output_type', choices=['record', 'perf_script'],
            default='record', help='output file\'s type')
    parser.add_argument('--output_permission', type=str, default='600',
            help='permission of the output file')
    parser.add_argument('--skip', type=int, metavar='<int>', default=20,
            help='number of first snapshots to skip')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    file_path = args.input

    result, err = _damon_result.parse_damon_result(file_path)
    if err:
        print('monitoring result file (%s) parsing failed (%s)' %
                (file_path, err))
        exit(1)

    if args.aggregate_interval != None:
        adjust_result(result, args.aggregate_interval, args.skip)
    _damon_result.write_damon_result(result, args.output, args.output_type)
    output_permission = int(args.output_permission, 8)
    if output_permission < 0o0 or output_permission > 0o777:
        print('wrong --output_permission (%s)' % args.output_permission)
        exit(1)
    os.chmod(args.output, output_permission)

if __name__ == '__main__':
    main()
