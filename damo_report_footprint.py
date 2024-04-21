# SPDX-License-Identifier: GPL-2.0

"Print out the distribution of the memory footprint of the given trace"

import argparse
import sys
import tempfile

import _damo_dist
import _damo_fmt_str
import _damo_records

def pr_dists(dists, percentiles, raw_number, nr_cols_bar, pr_all_footprints):
    print('# <percentile> <footprint>')
    if len(dists) == 0:
        print('# no snapshot')
        return
    print('# avr:\t%s' % _damo_fmt_str.format_sz(
        sum(dists) / len(dists), raw_number))

    if pr_all_footprints:
        for idx, fp in enumerate(dists):
            print('%s %s' % (idx, _damo_fmt_str.format_sz(fp, raw_number)))
        return

    if nr_cols_bar > 0:
        max_sz = 0
        for percentile in percentiles:
            fp_idx = int(percentile / 100.0 * len(dists))
            if fp_idx == len(dists):
                fp_idx -= 1
            fp = dists[fp_idx]
            if max_sz <= fp:
                max_sz = fp
        if max_sz > 0:
            sz_per_col = max_sz / nr_cols_bar
        else:
            sz_per_col = 1

    for percentile in percentiles:
        idx = int(percentile / 100.0 * len(dists))
        if idx == len(dists):
            idx -= 1
        fp = dists[idx]
        line = '%3d %15s' % (percentile,
            _damo_fmt_str.format_sz(fp, raw_number))
        if nr_cols_bar > 0:
            cols = int(fp / sz_per_col)
            remaining_cols = nr_cols_bar - cols
            line += ' |%s%s|' % ('*' * cols, ' ' * remaining_cols)
        print(line)

def set_argparser(parser):
    parser.add_argument('metric', choices=['vsz', 'rss', 'sys_used'],
                        help='memory footprint metric to show')
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
                        default='damon.data.mem_footprint',
                        help='input file name')
    parser.add_argument('--range', '-r', type=int, nargs=3,
                        metavar=('<start>', '<stop>', '<step>'),
                        default=[0,101,25],
                        help='range of wss percentiles to print')
    parser.add_argument('--sortby', '-s', choices=['time', 'size'],
                        default='size',
                        help='the metric to sort the footprints for')
    parser.add_argument('--plot', '-p', type=str, metavar='<file>',
                        help='plot the distribution to an image file')
    parser.add_argument('--nr_cols_bar', type=int, metavar='<num>',
                        default=59,
                        help='max columns of output')
    parser.add_argument('--raw_number', action='store_true',
                        help='use machine-friendly raw numbers')
    parser.add_argument('--all_footprint', action='store_true',
                        help='print not percentiles but all footprint values')
    parser.description = 'Show distribution of memory footprint'

def main(args):
    percentiles = range(args.range[0], args.range[1], args.range[2])
    wss_sort = True
    if args.sortby == 'time':
        wss_sort = False
    raw_number = args.raw_number

    footprint_snapshots = _damo_records.load_mem_footprint(args.input)
    dists = []
    for snapshot in footprint_snapshots:
        footprint_bytes = 0
        for pid, fp in snapshot.footprints.items():
            if args.metric == 'sys_used':
                if pid is not None:
                    continue
                footprint_bytes = (fp.total - fp.free) * 1024
            # ignore SysMemFootprint
            if pid is None:
                continue
            # todo: get real page size of the system
            if args.metric == 'vsz':
                footprint_bytes += fp.size * 4096
            elif args.metric == 'rss':
                footprint_bytes += fp.resident * 4096
        dists.append(footprint_bytes)

    if args.sortby == 'size':
        dists.sort()

    if args.plot:
        orig_stdout = sys.stdout
        tmp_path = tempfile.mkstemp()[1]
        tmp_file = open(tmp_path, 'w')
        sys.stdout = tmp_file
        raw_number = True
        args.nr_cols_bar = 0

    pr_dists(dists, percentiles, raw_number, args.nr_cols_bar,
            args.all_footprint)

    if args.plot:
        sys.stdout = orig_stdout
        tmp_file.flush()
        tmp_file.close()
        xlabel = 'runtime (percent)'
        if wss_sort:
            xlabel = 'percentile'
        err = _damo_dist.plot_dist(tmp_path, args.plot, xlabel,
                'memory footprint (kilobytes)')
        if err:
            print('plot failed (%s)' % err)
