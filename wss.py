#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Print out the distribution of the working set sizes of the given trace"

import argparse
import sys
import tempfile

import _dist
import _damon_result
import _fmt_nr

import adjust

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
    parser.add_argument('--nr_cols_bar', type=int, metavar='<num>',
            default=59,
            help='number of columns that is reserved for wss visualization')
    parser.add_argument('--raw_number', action='store_true',
            help='use machine-friendly raw numbers')

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
    raw_number = args.raw_number

    result = _damon_result.parse_damon_result(file_path, args.input_type)
    if not result:
        print('monitoring result file (%s) parsing failed' % file_path)
        exit(1)

    adjust.adjust_result(result, args.work_time, args.exclude_samples)

    orig_stdout = sys.stdout
    if args.plot:
        tmp_path = tempfile.mkstemp()[1]
        tmp_file = open(tmp_path, 'w')
        sys.stdout = tmp_file
        raw_number = True
        args.nr_cols_bar = 0

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

        nr_cols_bar = args.nr_cols_bar
        if nr_cols_bar:
            max_sz = 0
            for percentile in percentiles:
                wss_idx = int(percentile / 100.0 * len(wss_dist))
                if wss_idx == len(wss_dist):
                    wss_idx -= 1
                wss = wss_dist[wss_idx]
                if not max_sz or max_sz < wss:
                    max_sz = wss
            if max_sz != 0:
                sz_per_col = max_sz / nr_cols_bar
            else:
                sz_per_col = 1

        for percentile in percentiles:
            wss_idx = int(percentile / 100.0 * len(wss_dist))
            if wss_idx == len(wss_dist):
                wss_idx -= 1
            wss = wss_dist[wss_idx]
            line = '%3d %15s' % (percentile,
                _fmt_nr.format_sz(wss, raw_number))
            if nr_cols_bar:
                cols = int(wss/sz_per_col)
                remaining_cols = nr_cols_bar - cols
                line += ' |%s%s|' % ('*' * cols, ' ' * remaining_cols)
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
