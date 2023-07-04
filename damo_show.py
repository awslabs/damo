# SPDX-License-Identifier: GPL-2.0

import argparse
import json
import os

import _damo_fmt_str
import _damon
import _damon_args
import _damon_result

def apply_min_chars(min_chars, field_name, txt):
    # min_chars: [[<field name>, <number of min chars>]...]
    for name, nr in min_chars:
        try:
            nr = int(nr)
        except:
            print('wrong min_chars: %s' % min_chars)

        if name == field_name:
            if len(txt) >= nr:
                return txt
            txt += ' ' * (nr - len(txt))
            return txt
    return txt

def format_for(template, min_chars, field_name, txt):
    return template.replace(
            field_name, apply_min_chars(min_chars, field_name, txt))

def format_pretty(template, min_chars, idx, region, raw):
    template = template.replace('\\n', '\n')
    template = format_for(template, min_chars, '<index>',
            _damo_fmt_str.format_nr(idx, raw))
    template = format_for(template, min_chars, '<start address>',
            _damo_fmt_str.format_sz(region.start, raw))
    template = format_for(template, min_chars, '<end address>',
            _damo_fmt_str.format_sz(region.end, raw))
    template = format_for(template, min_chars, '<region size>',
            _damo_fmt_str.format_sz(region.end - region.start, raw))
    template = format_for(template, min_chars, '<access rate>',
            _damo_fmt_str.format_percent(region.nr_accesses.percent, raw))
    template = format_for(template, min_chars, '<age>',
            _damo_fmt_str.format_time_us(region.age.usec, raw))
    return template

def format_snapshot_tail_pretty(template, min_chars, snapshot, raw):
    template = template.replace('\\n', '\n')
    template = template.replace('<total bytes>',
            apply_min_chars(min_chars, '<total bytes>',
                _damo_fmt_str.format_sz(snapshot.total_bytes, raw)))
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
                if args.region_pretty == '':
                    continue
                if args.region_pretty == None:
                    args.region_pretty='<index> addr [<start address>, <end address>) (<region size>) access <access rate> age <age>'
                print(format_pretty(args.region_pretty, args.pretty_min_chars,
                    idx, r, args.raw_number))
            print('total sz: %s' % _damo_fmt_str.format_sz(total_size,
                args.raw_number))
            if args.snapshot_tail_pretty:
                print(format_snapshot_tail_pretty(
                    args.snapshot_tail_pretty, args.pretty_min_chars, snapshot,
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

    parser.add_argument('--snapshot_tail_pretty',
            help='snapshot output tail format')
    parser.add_argument('--region_pretty',
            help='region output format')
    parser.add_argument('--pretty_min_chars', nargs=2, default=[],
            metavar=('<field name> <number>'), action='append',
            help='minimum character for each field')
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
