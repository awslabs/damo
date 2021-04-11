#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Adjust damon.data with new attributes"

import argparse
import struct

import _damon_result


def set_argparser(parser):
    parser.add_argument('aggregate_interval', type=int,
            metavar='<microseconds>', help='new aggregation interval')
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--output', '-o', type=str, metavar='<file>',
            default='damon.adjusted.data', help='output file name')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    file_path = args.input

    result = _damon_result.parse_damon_result(file_path, 'record')
    if not result:
        print('monitoring result file (%s) parsing failed' % file_path)
        exit(1)

    snapshot_time = (result.end_time - result.start_time) / result.nr_snapshots
    nr_shots_in_aggr = max(round(args.aggregate_interval * 1000 /
        snapshot_time), 1)
    target_snapshots = result.target_snapshots

    start_time = 0
    end_time = 0
    nr_snapshots = int(max((result.nr_snapshots - 20), 0) / nr_shots_in_aggr)

    for tid in target_snapshots:
        # Skip first 20 snapshots as regions may not adjusted yet.
        snapshots = target_snapshots[tid][20:]
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

    _damon_result.write_damon_record(result, args.output, 2)

if __name__ == '__main__':
    main()
