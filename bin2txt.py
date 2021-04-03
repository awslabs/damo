#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import sys

import _parse_damon_result

def set_argparser(parser):
    parser.add_argument('--perf_script', action='store_true', default=False,
            help='input is a perf script output')
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    file_path = args.input

    if not os.path.isfile(file_path):
        print('input file (%s) is not exist' % file_path)
        exit(1)

    if not args.perf_script:
        result = _parse_damon_result.record_to_damon_result(file_path)
    else:
        result = _parse_damon_result.perf_script_to_damon_result(file_path)

    if not result:
        print('no monitoring result in the file')
        exit(1)

    print('start_time: ', result.start_time)
    for snapshot in result.snapshots:
        print('rel time: %16d' % (snapshot.monitored_time - result.start_time))
        print('nr_tasks:  1')
        print('target_id: ', snapshot.target_id)
        print('nr_regions: ', len(snapshot.regions))
        for r in snapshot.regions:
            print("%012x-%012x(%10d):\t%d" %
                    (r.start, r.end, r.end - r.start, r.nr_accesses))
        print()

if __name__ == '__main__':
    main()
