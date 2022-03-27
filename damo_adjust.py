#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Adjust a damon monitoring result with new attributes"

import argparse
import struct

import _damon_result

def adjust_result(result, aggregate_interval, nr_snapshots_to_skip): 
    interval = float(result.end_time - result.start_time) / result.nr_snapshots
    nr_shots_in_aggr = int(max(round(aggregate_interval * 1000 / interval), 1))
    target_snapshots = result.target_snapshots

    if nr_shots_in_aggr <= 1:
        return

    start_time = 0
    end_time = 0
    nr_snapshots = int(max((result.nr_snapshots - nr_snapshots_to_skip), 0) /
            nr_shots_in_aggr)

    for tid in target_snapshots:
        # Skip first several snapshots as regions may not adjusted yet.
        snapshots = target_snapshots[tid][nr_snapshots_to_skip:]
        if start_time == 0:
            start_time = snapshots[0].start_time
            end_time = snapshots[-1].end_time

        aggregated_snapshots = []
        for i in range(0, len(snapshots), nr_shots_in_aggr):
            to_aggregate = snapshots[i:
                    min(i + nr_shots_in_aggr, len(snapshots))]
            aggregated_snapshots.append(
                    _damon_result.aggregate_snapshots(to_aggregate))
        target_snapshots[tid] = aggregated_snapshots

    result.start_time = start_time
    result.end_time = end_time
    result.nr_snapshots = nr_snapshots

def set_argparser(parser):
    parser.add_argument('--aggregate_interval', type=int, default=None,
            metavar='<microseconds>', help='new aggregation interval')
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--input_type', choices=['record', 'perf_script'],
            default=None, help='input file\'s type')
    parser.add_argument('--output', '-o', type=str, metavar='<file>',
            default='damon.adjusted.data', help='output file name')
    parser.add_argument('--output_type', choices=['record', 'perf_script'],
            default='record', help='output file\'s type')
    parser.add_argument('--skip', type=int, metavar='<int>', default=20,
            help='number of first snapshots to skip')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    file_path = args.input

    result = _damon_result.parse_damon_result(file_path, args.input_type)
    if not result:
        print('monitoring result file (%s) parsing failed' % file_path)
        exit(1)

    if args.aggregate_interval != None:
        adjust_result(result, args.aggregate_interval, args.skip)
    _damon_result.write_damon_result(result, args.output, args.output_type,
            0o600)

if __name__ == '__main__':
    main()
