#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Adjust damon.data with new attributes"

import argparse
import struct

import _dist
import _recfile

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
                new_regions.append(
                        _dist.Region(region.start, r.start, region.nr_accesses))
            if r.end < region.end:
                new_regions.append(
                        _dist.Region(r.end, region.end, region.nr_accesses))

            for new_r in new_regions:
                add_region(regions, new_r, nr_acc_to_add)
            return
    regions.append(region)

def aggregate_snapshots(snapshots):
    new_snapshot = []   # list of workingset ([start, end, nr_accesses])
    for snapshot in snapshots:
        nr_acc_to_add = {}
        for region in snapshot:
            add_region(new_snapshot, region, nr_acc_to_add)
        for region in nr_acc_to_add:
            region.nr_accesses += nr_acc_to_add[region]

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
    tid_pattern_map = {}
    with open(file_path, 'rb') as f:
        _recfile.set_fmt_version(f)
        while True:
            timebin = f.read(16)
            if len(timebin) != 16:
                break

            if start_time == 0:
                start_time = _recfile.parse_time(timebin)
            end_time = _recfile.parse_time(timebin)

            nr_tasks = struct.unpack('I', f.read(4))[0]
            for t in range(nr_tasks):
                tid = _recfile.target_id(f)
                if not tid in tid_pattern_map:
                    tid_pattern_map[tid] = []
                tid_pattern_map[tid].append(_dist.access_patterns(f))

    aggr_int = (end_time - start_time) / (len(tid_pattern_map[tid]) - 1)
    nr_shots_in_aggr = max(round(args.aggregate_interval * 1000 / aggr_int), 1)

    for tid in tid_pattern_map:
        # Skip first 20 snapshots as regions may not adjusted yet.
        snapshots = tid_pattern_map[tid][20:]

        aggregated_snapshots = []
        for i in range(0, len(snapshots), nr_shots_in_aggr):
            to_aggregate = snapshots[i:
                    min(i + nr_shots_in_aggr, len(snapshots))]
            aggregated_snapshots.append(aggregate_snapshots(to_aggregate))
        tid_pattern_map[tid] = aggregated_snapshots

    now = start_time
    snapshot_idx = 0
    max_nr_snapshots = 0
    for snapshots in tid_pattern_map.values():
        max_nr_snapshots = max(max_nr_snapshots, len(snapshots))

    with open(args.output, 'wb') as f:
        # version
        f.write(b'damon_recfmt_ver')
        f.write(struct.pack('i', _recfile.fmt_version))

        for snapshot_idx in range(max_nr_snapshots):
            # time
            f.write(struct.pack('l', now // 1000000000))
            f.write(struct.pack('l', now % 1000000000))
            now += args.aggregate_interval * 1000

            # nr_tasks
            nr_tasks = 0
            for snapshots in tid_pattern_map.values():
                if len(snapshots) > snapshot_idx:
                    nr_tasks += 1
            f.write(struct.pack('I', nr_tasks))

            for tid in tid_pattern_map:
                snapshots = tid_pattern_map[tid]
                if len(snapshots) <= snapshot_idx:
                    continue

                if _recfile.fmt_version == 1:
                    f.write(struct.pack('i', tid))
                else:
                    f.write(struct.pack('L', tid))

                regions = snapshots[snapshot_idx]
                f.write(struct.pack('I', len(regions)))
                for r in regions:
                    f.write(struct.pack('L', r.start))
                    f.write(struct.pack('L', r.end))
                    f.write(struct.pack('I', r.nr_accesses))

if __name__ == '__main__':
    main()
