#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Print out the distribution of the working set sizes of the given trace"

import argparse
import sys
import tempfile

import _dist
import _damon_result
import _fmt_nr

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
    parser.add_argument('--plot_ascii', action='store_true',
            help='visualize in ascii art')
    parser.add_argument('--raw_number', action='store_true',
            help='use machine-friendly raw numbers')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.plot and args.plot_ascii:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        print('\'--plot\' and \'--plot_ascii\' cannot be given together\n')
        parser.print_help()
        exit(1)

    percentiles = [0, 25, 50, 75, 100]

    file_path = args.input
    if args.range:
        percentiles = range(args.range[0], args.range[1], args.range[2])
    wss_sort = True
    if args.sortby == 'time':
        wss_sort = False
    raw_number = args.raw_number

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
                aggregated_snapshots.append(
                        _damon_result.aggregate_snapshots(to_aggregate))
            result.target_snapshots[tid] = aggregated_snapshots

    orig_stdout = sys.stdout
    if args.plot:
        tmp_path = tempfile.mkstemp()[1]
        tmp_file = open(tmp_path, 'w')
        sys.stdout = tmp_file
        raw_number = True

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
        print('# avr:\t%s' % _fmt_nr.format_sz(
            sum(wss_dist) / len(wss_dist), raw_number))

        if args.plot_ascii:
            max_sz = 0
            for percentile in percentiles:
                thres_idx = int(percentile / 100.0 * len(wss_dist))
                if thres_idx == len(wss_dist):
                    thres_idx -= 1
                threshold = wss_dist[thres_idx]
                if not max_sz or max_sz < threshold:
                    max_sz = threshold
            nr_cols = 60
            sz_per_col = max_sz / 60

        for percentile in percentiles:
            thres_idx = int(percentile / 100.0 * len(wss_dist))
            if thres_idx == len(wss_dist):
                thres_idx -= 1
            threshold = wss_dist[thres_idx]
            line = '%3d%15s' % (percentile,
                _fmt_nr.format_sz(wss_dist[thres_idx], raw_number))
            if args.plot_ascii:
                line += ' %s' % ('-' * int(wss_dist[thres_idx] / sz_per_col))
            print(line)

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
