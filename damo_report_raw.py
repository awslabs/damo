# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import sys

import _damon_result
import _damo_fmt_str

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
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

    result, err = _damon_result.parse_damon_result(file_path)
    if err:
        print('parsing damon result file (%s) failed (%s)' %
                (file_path, err))
        exit(1)

    if not result:
        print('no monitoring result in the file')
        exit(1)

    for record in result.records:
        snapshots = record.snapshots
        if len(snapshots) == 0:
            continue

        base_time = snapshots[0].start_time
        print('base_time_absolute: %s\n' %
                _damo_fmt_str.format_time_ns(base_time, args.raw_number))

        for snapshot in snapshots:
            if args.duration:
                time_offset_sec = (snapshot.start_time - base_time) / 1000000000
                if time_offset_sec < args.duration[0]:
                    continue
                if time_offset_sec > args.duration[1]:
                    break
            print('monitoring_start:    %16s' %
                    _damo_fmt_str.format_time_ns(
                        snapshot.start_time - base_time, args.raw_number))
            print('monitoring_end:      %16s' %
                    _damo_fmt_str.format_time_ns(
                        snapshot.end_time - base_time, args.raw_number))
            print('monitoring_duration: %16s' %
                    _damo_fmt_str.format_time_ns(
                        snapshot.end_time - snapshot.start_time,
                        args.raw_number))
            print('target_id: %s' % record.target_id)
            print('nr_regions: %s' % len(snapshot.regions))
            print('# %10s %12s  %12s  %11s %5s' %
                    ('start_addr', 'end_addr', 'length', 'nr_accesses', 'age'))
            for r in snapshot.regions:
                print("%012x-%012x (%12s) %11d %5d" %
                        (r.start, r.end,
                            _damo_fmt_str.format_sz(r.end - r.start,
                                args.raw_number), r.nr_accesses.samples,
                                r.age.aggr_intervals
                                if r.age.aggr_intervals != None else -1))
            print('')

if __name__ == '__main__':
    main()
