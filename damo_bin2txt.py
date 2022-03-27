#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import sys

import _damon_result
import _damo_fmt_nr

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--input_type', choices=['record', 'perf_script'],
            default=None, help='input file\'s type')
    parser.add_argument('--duration', type=float, metavar='<seconds>', nargs=2,
            help='start and end time offset for record to parse')
    parser.add_argument('--raw_number', action='store_true',
            help='use machine-friendly raw numbers')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    file_path = args.input

    if not os.path.isfile(file_path):
        print('input file (%s) is not exist' % file_path)
        exit(1)

    if args.duration:
        print('read start')
        result, f, fmt_version = _damon_result.parse_damon_result_for(
                file_path, args.input_type, None, None, args.duration[0])
        print('now real read')
        result, f, fmt_version = _damon_result.parse_damon_result_for(
                file_path, args.input_type, f, fmt_version, args.duration[1])
        f.close()
    else:
        result = _damon_result.parse_damon_result(file_path, args.input_type)

    if not result:
        print('monitoring result file (%s) parsing failed' % file_path)
        exit(1)

    if not result:
        print('no monitoring result in the file')
        exit(1)

    for snapshots in result.target_snapshots.values():
        if len(snapshots) == 0:
            continue

        base_time = snapshots[0].start_time
        print('base_time_absolute: %s\n' %
                _damo_fmt_nr.format_time(base_time, args.raw_number))

        for snapshot in snapshots:
            print('monitoring_start:    %16s' %
                    _damo_fmt_nr.format_time(
                        snapshot.start_time - base_time, args.raw_number))
            print('monitoring_end:      %16s' %
                    _damo_fmt_nr.format_time(
                        snapshot.end_time - base_time, args.raw_number))
            print('monitoring_duration: %16s' %
                    _damo_fmt_nr.format_time(
                        snapshot.end_time - snapshot.start_time,
                        args.raw_number))
            print('target_id: %s' % snapshot.target_id)
            print('nr_regions: %s' % len(snapshot.regions))
            for r in snapshot.regions:
                print("%012x-%012x(%12s):\t%d" %
                        (r.start, r.end,
                            _damo_fmt_nr.format_sz(r.end - r.start,
                                args.raw_number), r.nr_accesses))
            print('')

if __name__ == '__main__':
    main()
