# SPDX-License-Identifier: GPL-2.0

"Print out the distribution of the memory footprint of the given trace"

import sys
import tempfile

import _damo_dist
import _damo_fmt_str
import _damo_records

def set_argparser(parser):
    parser.add_argument('metric', choices=['vsz', 'rss', 'sys_used', 'all'],
                        default='all', nargs='?',
                        help='memory footprint metric to show')
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
                        default='damon.data.mem_footprint',
                        help='input file name')
    parser.add_argument('--range', '-r', type=int, nargs=3,
                        metavar=('<start>', '<stop>', '<step>'),
                        default=[0,101,25],
                        help='range of percentiles to print')
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

def get_dists(records, metric, do_sort):
    dists = []
    footprint_snapshots = _damo_records.load_mem_footprint(records)
    for snapshot in footprint_snapshots:
        footprint_bytes = 0
        for pid, fp in snapshot.footprints.items():
            if metric == 'sys_used':
                if pid is not None:
                    continue
                footprint_bytes = (fp.total - fp.free) * 1024
            # ignore SysMemFootprint
            if pid is None:
                continue
            # todo: get real page size of the system
            if metric == 'vsz':
                footprint_bytes += fp.size * 4096
            elif metric == 'rss':
                footprint_bytes += fp.resident * 4096
        dists.append(footprint_bytes)
    if do_sort:
        dists.sort()
    return dists

def main(args):
    if args.metric == 'all':
        for metric in ['vsz', 'rss', 'sys_used']:
            args.metric = metric
            main(args)
        return

    dists = get_dists(args.input, args.metric, args.sortby == 'size')

    percentiles = range(args.range[0], args.range[1], args.range[2])
    raw_number = args.raw_number
    if not args.plot:
        _damo_dist.pr_dists(
                args.metric, dists, percentiles, args.all_footprint,
                _damo_fmt_str.format_sz, raw_number, args.nr_cols_bar)
        return

    tmp_path = tempfile.mkstemp()[1]
    with open(tmp_path, 'w') as f:
        f.write(_damo_dist.fmt_dists(
            args.metric, dists, percentiles, args.all_footprint,
            _damo_fmt_str.format_sz, True, 0))

    sort_by_sz = True
    if args.sortby == 'time':
        sort_by_sz = False

    xlabel = 'runtime (percent)'
    if sort_by_sz:
        xlabel = 'percentile'
    err = _damo_dist.plot_dist(tmp_path, args.plot, xlabel,
            'memory footprint (kilobytes)')
    if err:
        print('plot failed (%s)' % err)
