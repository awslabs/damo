#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Adjust damon.data with new attributes"

import argparse
import struct

import _damon_result

def regions_intersect(r1, r2):
    return not (r1.end <= r2.start or r2.end <= r1.start)

def add_region(regions, region, nr_acc_to_add):
    for r in regions:
        if regions_intersect(r, region):
            if not r in nr_acc_to_add:
                nr_acc_to_add[r] = 0
            nr_acc_to_add[r] = max(nr_acc_to_add[r], region.nr_accesses)

            new_regions = []
            if region.start < r.start:
                new_regions.append(_damon_result.DAMONRegion(
                    region.start, r.start, region.nr_accesses))
            if r.end < region.end:
                new_regions.append(_damon_result.DAMONRegion(
                        r.end, region.end, region.nr_accesses))

            for new_r in new_regions:
                add_region(regions, new_r, nr_acc_to_add)
            return
    regions.append(region)

def aggregate_snapshots(snapshots):
    new_regions = []
    for snapshot in snapshots:
        nr_acc_to_add = {}
        for region in snapshot.regions:
            add_region(new_regions, region, nr_acc_to_add)
        for region in nr_acc_to_add:
            region.nr_accesses += nr_acc_to_add[region]

    new_snapshot = _damon_result.DAMONSnapshot(snapshots[0].start_time,
            snapshots[-1].end_time, snapshots[0].target_id)
    new_snapshot.regions = new_regions
    return new_snapshot

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

    start_time = 0
    end_time = 0

    result = _damon_result.parse_damon_result(file_path, 'record')
    if not result:
        print('monitoring result file (%s) parsing failed' % file_path)
        exit(1)

    snapshot_time = (result.end_time - result.start_time) / result.nr_snapshots
    nr_shots_in_aggr = max(round(args.aggregate_interval * 1000 /
        snapshot_time), 1)
    target_snapshots = result.snapshots

    for tid in target_snapshots:
        # Skip first 20 snapshots as regions may not adjusted yet.
        snapshots = target_snapshots[tid][20:]
        if start_time == 0:
            start_time = snapshots[0].start_time

        aggregated_snapshots = []
        for i in range(0, len(snapshots), nr_shots_in_aggr):
            to_aggregate = snapshots[i:
                    min(i + nr_shots_in_aggr, len(snapshots))]
            aggregated_snapshots.append(aggregate_snapshots(to_aggregate))
        target_snapshots[tid] = aggregated_snapshots

    now = start_time
    snapshot_idx = 0
    max_nr_snapshots = 0
    for snapshots in target_snapshots.values():
        max_nr_snapshots = max(max_nr_snapshots, len(snapshots))

    with open(args.output, 'wb') as f:
        # version
        f.write(b'damon_recfmt_ver')
        f.write(struct.pack('i', 2))

        for snapshot_idx in range(max_nr_snapshots):
            # time
            f.write(struct.pack('l', now // 1000000000))
            f.write(struct.pack('l', now % 1000000000))
            now += args.aggregate_interval * 1000

            # nr_tasks
            nr_tasks = 0
            for snapshots in target_snapshots.values():
                if len(snapshots) > snapshot_idx:
                    nr_tasks += 1
            f.write(struct.pack('I', nr_tasks))

            for tid in target_snapshots:
                snapshots = target_snapshots[tid]
                if len(snapshots) <= snapshot_idx:
                    continue

                f.write(struct.pack('L', tid))

                regions = snapshots[snapshot_idx].regions
                f.write(struct.pack('I', len(regions)))
                for r in regions:
                    f.write(struct.pack('L', r.start))
                    f.write(struct.pack('L', r.end))
                    f.write(struct.pack('I', r.nr_accesses))

if __name__ == '__main__':
    main()
