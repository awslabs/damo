# SPDX-License-Identifier: GPL-2.0

import argparse
import json
import os

import _damo_fmt_str
import _damon
import _damon_args
import _damon_result

def format_pretty(template, idx, region, raw):
    template = template.replace('<index>', '%s' % idx)
    template = template.replace('<start address>',
            _damo_fmt_str.format_sz(region.start, raw))
    template = template.replace('<end address>',
            _damo_fmt_str.format_sz(region.end, raw))
    template = template.replace('<region size>',
            _damo_fmt_str.format_sz(region.end - region.start, raw))
    template = template.replace('<access rate>',
            region.nr_accesses.to_str(_damon.unit_percent, raw))
    template = template.replace('<age>',
            _damo_fmt_str.format_time_us(region.age.usec, raw))
    return template

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
        if len(records) > 1:
            print('kdamond %s / context %s / scheme %s' %
                    (record.kdamond_idx, record.context_idx,
                        record.scheme_idx))
        if len(snapshots) > 1:
            print('base_time_absolute: %s\n' %
                    _damo_fmt_str.format_time_ns(base_time, args.raw_number))

        for sidx, snapshot in enumerate(snapshots):
            if len(snapshots) > 1:
                print('monitored time: [%s, %s] (%s)' %
                        (_damo_fmt_str.format_time_ns(
                            snapshot.start_time - base_time, args.raw_number),
                            _damo_fmt_str.format_time_ns(
                                snapshot.end_time - base_time, args.raw_number),
                            _damo_fmt_str.format_time_ns(
                                snapshot.end_time - snapshot.start_time,
                                args.raw_number)))
            if record.target_id != None:
                print('target_id: %s' % record.target_id)
            if args.total_sz_only and snapshot.total_bytes != None:
                print('total sz: %s' %
                        _damo_fmt_str.format_sz(snapshot.total_bytes,
                            args.raw_number))
                continue
            total_size = 0
            for idx, r in enumerate(snapshot.regions):
                total_size += r.end - r.start
                if args.total_sz_only:
                    continue
                r.nr_accesses.add_unset_unit(record.intervals)
                r.age.add_unset_unit(record.intervals)
                if args.pretty:
                    print(format_pretty(args.pretty, idx, r, args.raw_number))
                    continue

                address_range = '[%s, %s)' % (
                        _damo_fmt_str.format_sz(r.start, args.raw_number),
                        _damo_fmt_str.format_sz(r.end, args.raw_number))
                region_size = _damo_fmt_str.format_sz((r.end - r.start),
                        args.raw_number)
                access_rate = r.nr_accesses.to_str(_damon.unit_percent,
                        args.raw_number)
                age = _damo_fmt_str.format_time_us(r.age.usec, args.raw_number)
                print('%3d addr %s (%s) access %s age %s' % (
                    idx, address_range, region_size, access_rate, age))
            print('total sz: %s' % _damo_fmt_str.format_sz(total_size,
                args.raw_number))
            if sidx < len(snapshots) - 1:
                print('')

def filter_by_pattern(record, access_pattern):
    sz_bytes = access_pattern.sz_bytes
    nr_acc = access_pattern.nr_acc_min_max
    age = access_pattern.age_min_max

    for snapshot in record.snapshots:
        filtered = []
        for region in snapshot.regions:
            sz = region.end - region.start
            if sz < sz_bytes[0] or sz_bytes[1] < sz:
                continue
            intervals = record.intervals
            if intervals == None:
                filtered.append(region)
                continue
            region.nr_accesses.add_unset_unit(intervals)
            freq = region.nr_accesses.percent
            if freq < nr_acc[0].percent or nr_acc[1].percent < freq:
                continue
            region.age.add_unset_unit(intervals)
            usecs = region.age.usec
            if usecs < age[0].usec or age[1].usec < usecs:
                continue
            filtered.append(region)
        snapshot.regions = filtered

def set_argparser(parser):
    '''
    TODOs
    - schemes tried regions based filtering
    - time based filtering
    - printing heatbar (bar of the size colored with access rate)
    - printing only heatbars (becomes heatmap)
    - sort by priority with priority weights (become histogram)
    - collapse by time
    - collapse by priority value (more histogram control)
    '''
    _damon_args.set_common_argparser(parser)
    parser.add_argument('--sz_region', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max size of regions (bytes)')
    parser.add_argument('--access_rate', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max access rate of regions (percent)')
    parser.add_argument('--age', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max age of regions (seconds)')

    parser.add_argument('--input_file', metavar='<file>',
            help='source of the access pattern to show')
    parser.add_argument('--tried_regions_of', nargs=3, type=int,
            action='append',
            metavar=('<kdamond idx>', '<context idx>', '<scheme idx>'),
            help='show tried regions of given schemes')

    parser.add_argument('--pretty',
            help='output format for each region')
    parser.add_argument('--total_sz_only', action='store_true',
            help='print only total size of the regions')
    parser.add_argument('--raw_number', action='store_true',
            help='use machine-friendly raw numbers')
    parser.add_argument('--json', action='store_true',
            help='print in json format')
    parser.description='Show DAMON-monitored access pattern'
    parser.epilog='If --input_file is not provided, capture snapshot'

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    access_pattern = _damon.DamosAccessPattern(args.sz_region,
            args.access_rate, _damon.unit_percent, args.age * 1000000,
            _damon.unit_usec)

    if args.input_file == None:
        _damon.ensure_root_and_initialized(args)

        records, err = _damon_result.get_snapshot_records(access_pattern,
                args.total_sz_only)
        if err != None:
            print(err)
            exit(1)
    else:
        if not os.path.isfile(args.input_file):
            print('--input_file (%s) is not file' % args.input_file)
            exit(1)

        records, err = _damon_result.parse_records_file(args.input_file)
        if err:
            print('parsing damon result file (%s) failed (%s)' %
                    (args.input_file, err))
            exit(1)
        for record in records:
            filter_by_pattern(record, access_pattern)

    for record in records:
        pr_records(args, records)

if __name__ == '__main__':
    main()
