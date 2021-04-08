#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import sys

import _parse_damon_result

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--input_type', choices=['record', 'perf_script'],
            default=None, help='input file\'s type')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    file_path = args.input

    if not os.path.isfile(file_path):
        print('input file (%s) is not exist' % file_path)
        exit(1)

    result = _parse_damon_result.parse_damon_result(file_path, args.input_type)
    if not result:
        print('monitoring result file (%s) parsing failed' % file_path)
        exit(1)

    if not result:
        print('no monitoring result in the file')
        exit(1)

    for snapshots in result.snapshots.values():
        if len(snapshots) == 0:
            continue

        base_time = snapshots[0].start_time
        print('base_time_absolute: %s\n' % base_time)

        for snapshot in snapshots:
            print('monitoring_start:    %16d' %
                (snapshot.start_time - base_time))
            print('monitoring_end:      %16d' %
                (snapshot.end_time - base_time))
            print('monitoring_duration: %16d' %
                (snapshot.end_time - snapshot.start_time))
            print('target_id:', snapshot.target_id)
            print('nr_regions:', len(snapshot.regions))
            for r in snapshot.regions:
                print("%012x-%012x(%10d):\t%d" %
                        (r.start, r.end, r.end - r.start, r.nr_accesses))
            print()

if __name__ == '__main__':
    main()
