# SPDX-License-Identifier: GPL-2.0

"Print out the distribution of the working set sizes of the given trace"

import argparse
import sys
import tempfile

import _damo_dist
import _damo_fmt_str
import _damon_result

def get_wss_dists(records, acc_thres, sz_thres, do_sort):
    wss_dists = {}
    for record in records:
        wss_dist = []
        for snapshot in record.snapshots:
            wss = 0
            for r in snapshot.regions:
                # Ignore regions not fulfill working set conditions
                if r.nr_accesses.samples < acc_thres:
                    continue
                if r.size() < sz_thres:
                    continue
                wss += r.size()
            wss_dist.append(wss)
        if do_sort:
            wss_dist.sort(reverse=False)
        wss_dists[record.target_id] = wss_dist
    return wss_dists

def pr_wss_dists(wss_dists, percentiles, raw_number, nr_cols_bar, pr_all_wss):
    print('# <percentile> <wss>')
    for tid, wss_dist in wss_dists.items():
        print('# target_id\t%s' % tid)
        if len(wss_dist) == 0:
            print('# no snapshot')
            return
        print('# avr:\t%s' % _damo_fmt_str.format_sz(
            sum(wss_dist) / len(wss_dist), raw_number))

        if pr_all_wss:
            for idx, wss in enumerate(wss_dist):
                print('%s %s' % (idx, _damo_fmt_str.format_sz(wss, raw_number)))
            return

        if nr_cols_bar > 0:
            max_sz = 0
            for percentile in percentiles:
                wss_idx = int(percentile / 100.0 * len(wss_dist))
                if wss_idx == len(wss_dist):
                    wss_idx -= 1
                wss = wss_dist[wss_idx]
                if max_sz <= wss:
                    max_sz = wss
            if max_sz > 0:
                sz_per_col = max_sz / nr_cols_bar
            else:
                sz_per_col = 1

        for percentile in percentiles:
            wss_idx = int(percentile / 100.0 * len(wss_dist))
            if wss_idx == len(wss_dist):
                wss_idx -= 1
            wss = wss_dist[wss_idx]
            line = '%3d %15s' % (percentile,
                _damo_fmt_str.format_sz(wss, raw_number))
            if nr_cols_bar > 0:
                cols = int(wss / sz_per_col)
                remaining_cols = nr_cols_bar - cols
                line += ' |%s%s|' % ('*' * cols, ' ' * remaining_cols)
            print(line)

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--range', '-r', type=int, nargs=3,
            metavar=('<start>', '<stop>', '<step>'), default=[0,101,25],
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
    parser.add_argument('--all_wss', action='store_true',
            help='Do not print percentile but all calculated wss')
    parser.description = 'Show distribution of working set size'

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    file_path = args.input
    percentiles = range(args.range[0], args.range[1], args.range[2])
    wss_sort = True
    if args.sortby == 'time':
        wss_sort = False
    raw_number = args.raw_number

    records, err = _damon_result.parse_records_file(file_path)
    if err != None:
        print('monitoring result file (%s) parsing failed (%s)' %
                (file_path, err))
        exit(1)

    _damon_result.adjust_records(records, args.work_time, args.exclude_samples)
    wss_dists = get_wss_dists(records, args.acc_thres, args.sz_thres, wss_sort)

    if args.plot:
        orig_stdout = sys.stdout
        tmp_path = tempfile.mkstemp()[1]
        tmp_file = open(tmp_path, 'w')
        sys.stdout = tmp_file
        raw_number = True
        args.nr_cols_bar = 0

    pr_wss_dists(wss_dists, percentiles, raw_number, args.nr_cols_bar,
            args.all_wss)

    if args.plot:
        sys.stdout = orig_stdout
        tmp_file.flush()
        tmp_file.close()
        xlabel = 'runtime (percent)'
        if wss_sort:
            xlabel = 'percentile'
        err = _damo_dist.plot_dist(tmp_path, args.plot, xlabel,
                'working set size (bytes)')
        if err:
            print('plot failed (%s)' % err)

if __name__ == '__main__':
    main()
