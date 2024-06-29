# SPDX-License-Identifier: GPL-2.0

"Print out the distribution of the working set sizes of the given trace"

import sys
import tempfile

import _damo_dist
import _damo_fmt_str
import _damo_records

def get_wss_dists(records, acc_thres, sz_thres, do_sort, collapse_targets):
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
    if collapse_targets is True:
        collapsed_dist = []
        for t, dist in wss_dists.items():
            for idx, wss in enumerate(dist):
                if len(collapsed_dist) <= idx:
                    collapsed_dist.append(wss)
                else:
                    collapsed_dist[idx] += wss
        wss_dists = {0: collapsed_dist}
    return wss_dists

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
    parser.add_argument('--per_target', action='store_false',
                        dest='collapse_targets',
                        help='Report workingset size per monitoring target')
    parser.add_argument('--collapse_targets', action='store_true',
                        help='Collapse targets in the record into one')
    parser.description = 'Show distribution of working set size'

def main(args):
    file_path = args.input
    percentiles = range(args.range[0], args.range[1], args.range[2])
    wss_sort = True
    if args.sortby == 'time':
        wss_sort = False
    raw_number = args.raw_number

    records, err = _damo_records.get_records(record_file=file_path)
    if err != None:
        print('monitoring result file (%s) parsing failed (%s)' %
                (file_path, err))
        exit(1)

    _damo_records.adjust_records(records, args.work_time, args.exclude_samples)
    wss_dists = get_wss_dists(records, args.acc_thres, args.sz_thres, wss_sort,
                              args.collapse_targets)

    if not args.plot:
        for tid, dists in wss_dists.items():
            print('# target_id\t%s' % tid)
            _damo_dist.pr_dists(
                    'wss', dists, percentiles, args.all_wss,
                    _damo_fmt_str.format_sz, raw_number, args.nr_cols_bar)
        return

    tmp_path = tempfile.mkstemp()[1]
    with open(tmp_path, 'w') as f:
        for tid, dists in wss_dists.items():
            f.write('# target_id\t%s\n' % tid)
            f.write( _damo_dist.fmt_dists(
                'wss', dists, percentiles, args.all_wss,
                _damo_fmt_str.format_sz, True, 0))

    xlabel = 'runtime (percent)'
    if wss_sort:
        xlabel = 'percentile'
    err = _damo_dist.plot_dist(tmp_path, args.plot, xlabel,
            'working set size (bytes)')
    if err:
        print('plot failed (%s)' % err)
