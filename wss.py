#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Print out the distribution of the working set sizes of the given trace"

import argparse
import sys
import tempfile

import _dist
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
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--input_type', choices=['record', 'perf_script'],
            default=None, help='input file\'s type')
    parser.add_argument('--range', '-r', type=int, nargs=3,
            metavar=('<start>', '<stop>', '<step>'),
            help='range of wss percentiles to print')
    parser.add_argument('--exclude_samples', type=int, default=20,
            metavar='<# samples>',
            help='number of first samples to be excluded')
    parser.add_argument('--acc_thres', '-t', type=int, default=1,
            metavar='<# accesses>',
            help='minimal number of accesses for treated as working set')
    parser.add_argument('--sz_thres', type=int, default=1,
            metavar='<size>',
            help='minimal size of region for treated as working set')
    parser.add_argument('--work_time', type=int, default=1,
            metavar='<micro-seconds>',
            help='supposed time for each unit of the work')
    parser.add_argument('--sortby', '-s', choices=['time', 'size'],
            help='the metric to be used for the sort of the working set sizes')
    parser.add_argument('--plot', '-p', type=str, metavar='<file>',
            help='plot the distribution to an image file')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    percentiles = [0, 25, 50, 75, 100]

    file_path = args.input
    if args.range:
        percentiles = range(args.range[0], args.range[1], args.range[2])
    wss_sort = True
    if args.sortby == 'time':
        wss_sort = False

    result = _damon_result.parse_damon_result(file_path, args.input_type)
    if not result:
        print('monitoring result file (%s) parsing failed' % file_path)
        exit(1)

    snapshot_time = (result.end_time - result.start_time) / result.nr_snapshots
    nr_shots_in_aggr = max(round(args.work_time * 1000 / snapshot_time), 1)
    target_snapshots = result.target_snapshots

    if nr_shots_in_aggr > 1:
        for tid in target_snapshots:
            # Skip first N snapshots as regions may not adjusted yet.
            snapshots = target_snapshots[tid][args.exclude_samples:]

            aggregated_snapshots = []
            for i in range(0, len(snapshots), nr_shots_in_aggr):
                to_aggregate = snapshots[i:
                        min(i + nr_shots_in_aggr, len(snapshots))]
                aggregated_snapshots.append(aggregate_snapshots(to_aggregate))
            result.target_snapshots[tid] = aggregated_snapshots

    orig_stdout = sys.stdout
    if args.plot:
        tmp_path = tempfile.mkstemp()[1]
        tmp_file = open(tmp_path, 'w')
        sys.stdout = tmp_file

    print('# <percentile> <wss>')
    for tid in result.target_snapshots.keys():
        snapshots = result.target_snapshots[tid]
        wss_dist = []
        for idx, snapshot in enumerate(snapshots):
            wss = 0
            for r in snapshot.regions:
                # Ignore regions not fulfill working set conditions
                if r.nr_accesses < args.acc_thres:
                    continue
                if r.end - r.start < args.sz_thres:
                    continue
                wss += r.end - r.start
            wss_dist.append(wss)
        if wss_sort:
            wss_dist.sort(reverse=False)

        print('# target_id\t%s' % tid)
        print('# avr:\t%d' % (sum(wss_dist) / len(wss_dist)))
        for percentile in percentiles:
            thres_idx = int(percentile / 100.0 * len(wss_dist))
            if thres_idx == len(wss_dist):
                thres_idx -= 1
            threshold = wss_dist[thres_idx]
            print('%d\t%d' % (percentile, wss_dist[thres_idx]))

    if args.plot:
        sys.stdout = orig_stdout
        tmp_file.flush()
        tmp_file.close()
        xlabel = 'runtime (percent)'
        if wss_sort:
            xlabel = 'percentile'
        _dist.plot_dist(tmp_path, args.plot, xlabel,
                'working set size (bytes)')

if __name__ == '__main__':
    main()
