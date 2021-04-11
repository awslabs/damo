#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"Print out distribution of the number of regions in the given record"

import argparse
import sys
import tempfile

import _dist
import _damon_result

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--input_type', choices=['record', 'perf_script'],
            default=None, help='input file\'s type')
    parser.add_argument('--range', '-r', type=int, nargs=3,
            metavar=('<start>', '<stop>', '<step>'),
            help='range of percentiles to print')
    parser.add_argument('--sortby', '-s', choices=['time', 'size'],
            help='the metric to be used for sorting the number of regions')
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
    nr_regions_sort = True
    if args.sortby == 'time':
        nr_regions_sort = False

    result = _damon_result.parse_damon_result(file_path, args.input_type)
    if not result:
        print('monitoring result file (%s) parsing failed' % file_path)
        exit(1)

    orig_stdout = sys.stdout
    if args.plot:
        tmp_path = tempfile.mkstemp()[1]
        tmp_file = open(tmp_path, 'w')
        sys.stdout = tmp_file

    print('# <percentile> <# regions>')

    for tid in result.target_snapshots.keys():
        # Skip firs 20 regions as those would not adaptively adjusted
        snapshots = result.target_snapshots[tid][20:]
        nr_regions_dist = []
        for snapshot in snapshots:
            nr_regions_dist.append(len(snapshot.regions))
        if nr_regions_sort:
            nr_regions_dist.sort(reverse=False)

        print('# target_id\t%s' % tid)
        print('# avr:\t%d' % (sum(nr_regions_dist) / len(nr_regions_dist)))
        for percentile in percentiles:
            thres_idx = int(percentile / 100.0 * len(nr_regions_dist))
            if thres_idx == len(nr_regions_dist):
                thres_idx -= 1
            threshold = nr_regions_dist[thres_idx]
            print('%d\t%d' % (percentile, nr_regions_dist[thres_idx]))

    if args.plot:
        sys.stdout = orig_stdout
        tmp_file.flush()
        tmp_file.close()
        xlabel = 'runtime (percent)'
        if nr_regions_sort:
            xlabel = 'percentile'
        _dist.plot_dist(tmp_path, args.plot, xlabel,
                'number of monitoring target regions')

if __name__ == '__main__':
    main()
