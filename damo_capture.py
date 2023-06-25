# SPDX-License-Identifier: GPL-2.0

import argparse
import json
import os
import sys

import _damo_fmt_str
import _damon
import _damon_args
import _damon_result

def pr_records(args, records):
    if args.json:
        print(json.dumps([r.to_kvpairs(args.raw_number)
            for r in records], indent=4))
        exit(0)

    for record in records:
        snapshots = record.snapshots
        if len(snapshots) == 0:
            continue

        base_time = snapshots[0].start_time
        print('base_time_absolute: %s\n' %
                _damo_fmt_str.format_time_ns(base_time, args.raw_number))

        for snapshot in snapshots:
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
                print(r.to_str(args.raw_number, record.intervals))
            print('')

def set_argparser(parser):
    _damon_args.set_common_argparser(parser)
    parser.add_argument('--raw_number', action='store_true',
            help='use machine-friendly raw numbers')
    parser.add_argument('--json', action='store_true',
            help='print in json format')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_and_initialized(args)

    records, err = _damon_result.get_snapshot_records(
            _damon.DamosAccessPattern())
    if err != None:
        print(err)
        exit(1)

    for record in records:
        pr_records(args, records)

if __name__ == '__main__':
    main()
