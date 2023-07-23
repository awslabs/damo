# SPDX-License-Identifier: GPL-2.0

import argparse
import copy
import json
import os
import random
import time

import _damo_fmt_str
import _damon
import _damon_args
import _damon_result

record_formatters = {
        '<kdamond index>': lambda record, raw:
            '%s' % record.kdamond_idx,
        '<context index>': lambda record, raw:
            '%s' % record.context_idx,
        '<scheme index>': lambda record, raw:
            '%s' % record.scheme_idx,
        '<target id>': lambda record, raw:
            '%s' % record.target_id,
        '<record start abs time>': lambda record, raw:
            _dmo_fmt_str.format_ns(record.snapshots[0].start_time, raw),
        '<record duration>': lambda record, raw:
            _damo_fmt_str.format_time_ns(
                record.snapshots[-1].end_time - record.snapshots[0].start_time,
                raw)
            }

snapshot_formatters = {
        '<total bytes>': lambda snapshot, record, raw:
            _damo_fmt_str.format_sz(snapshot.total_bytes, raw),
        '<monitor duration>': lambda snapshot, record, raw:
            _damo_fmt_str.format_time_ns(
                snapshot.end_time - snapshot.start_time, raw),
        '<monitor start time>': lambda snapshot, record, raw:
            _damo_fmt_str.format_time_ns(
                snapshot.start_time - record.snapshots[0].start_time, raw),
        '<monitor end time>': lambda snapshot, record, raw:
            _damo_fmt_str.format_time_ns(
                snapshot.end_time - record.snapshots[0].start_time, raw),
        '<monitor start abs time>': lambda snapshot, record, raw:
            _damo_fmt_str.format_time_ns(snapshot.start_time, raw),
        '<monitor end abs time>': lambda snapshot, record, raw:
            _damo_fmt_str.format_time_ns(snapshot.end_time, raw),
        '<number of regions>': lambda snapshot, record, raw:
            _damo_fmt_str.format_nr(len(snapshot.regions), raw),
            }

region_formatters = {
        '<index>': lambda index, region, raw, mms:
            _damo_fmt_str.format_nr(index, raw),
        '<start address>': lambda index, region, raw, mms:
            _damo_fmt_str.format_sz(region.start, raw),
        '<end address>': lambda index, region, raw, mms:
            _damo_fmt_str.format_sz(region.end, raw),
        '<region size>': lambda index, region, raw, mms:
            _damo_fmt_str.format_sz(region.size(), raw),
        '<access rate>': lambda index, region, raw, mms:
            _damo_fmt_str.format_percent(region.nr_accesses.percent, raw),
        '<age>': lambda index, region, raw, mms:
            _damo_fmt_str.format_time_us(region.age.usec, raw),
        '<size_bar>': lambda index, region, raw, mms:
           size_bar(region, mms, 0, 20),
        }

formatters = {
        'record': record_formatters,
        'snapshot': snapshot_formatters,
        'region': region_formatters
        }

def __age_size_heat_box(region, record,
        usec_per_column, bytes_per_row, nr_per_access_rate_percent):
    '''
    Generate a string that represents a box.  The box represents age, size, and
    heat of the region with length (number of columns), height (number of
    rows), and number, respectively.
    '''
    nr_columns = int(region.age.usec / usec_per_column)
    nr_rows = int(region.size() / bytes_per_row)
    heat_nr = int(region.nr_accesses.percent / nr_per_access_rate_percent)
    return '\n'.join([('%d' % heat_nr) * nr_columns] * nr_rows)

class MinMaxOfRecords:
    min_sz_region = None
    max_sz_region = None
    min_access_rate_percent = None
    max_access_rate_percent = None
    min_age_us = None
    max_age_us = None

    def set_fields(self, region, intervals):
        region.nr_accesses.add_unset_unit(intervals)
        region.age.add_unset_unit(intervals)

        if self.min_sz_region == None or region.size() < self.min_sz_region:
            self.min_sz_region = region.size()
        if self.max_sz_region == None or region.size() > self.max_sz_region:
            self.max_sz_region = region.size()
        if (self.min_access_rate_percent == None or
                region.nr_accesses.percent < self.min_access_rate_percent):
            self.min_access_rate_percent = region.nr_accesses.percent
        if (self.max_access_rate_percent == None or
                region.nr_accesses.percent > self.max_access_rate_percent):
            self.max_access_rate_percent = region.nr_accesses.percent
        if self.min_age_us == None or region.age.usec < self.min_age_us:
            self.min_age_us = region.age.usec
        if self.max_age_us == None or region.age.usec > self.max_age_us:
            self.max_age_us = region.age.usec

    def __init__(self, records):
        for record in records:
            for snapshot in record.snapshots:
                for region in snapshot.regions:
                    self.set_fields(region, record.intervals)

def rescale_val(val, orig_scale_minmax, new_scale_minmax):
    '''Return a value in new scale

    Parameters
    ----------
    val : int, float
        The value to rescale
    orig_scale_minmax : list
        min/max values of original scale
    new_scale_minmax : list
        min/max values of new scale

    Returns
    -------
    float
        The rescaled value
    '''
    orig_length = orig_scale_minmax[1] - orig_scale_minmax[0]
    new_length = new_scale_minmax[1] - new_scale_minmax[0]
    ratio = new_length / orig_length
    return (val - orig_scale_minmax[0]) * ratio + new_scale_minmax[0]

def size_bar(region, minmaxs, min_cols, max_cols):
    nr_cols = int(rescale_val(region.size(),
            [minmaxs.min_sz_region, minmaxs.max_sz_region],
            [min_cols, max_cols]))
    return '<%s>' % ('-' * nr_cols)

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

def format_pr(template, min_chars, index, region, snapshot, record, raw, mms):
    if template == '':
        return
    for category, category_formatters in formatters.items():
        for field_name, formatter in category_formatters.items():
            if template.find(field_name) == -1:
                continue
            if category == 'record':
                txt = formatter(record, raw)
            elif category == 'snapshot':
                txt = formatter(snapshot, record, raw)
            elif category == 'region':
                txt = formatter(index, region, raw, mms)
            txt = apply_min_chars(min_chars, field_name, txt)
            template = template.replace(field_name, txt)
    template = template.replace('\\n', '\n')
    print(template)

def set_formats(args, records):
    if args.format_record_head == None:
        if len(records) > 1:
            args.format_record_head = 'kdamond <kdamond index> / context <context index> / scheme <scheme index> / target id <target id> / recorded for <record duration> from <record start abs time>'
        else:
            args.format_record_head = ''

    if args.format_snapshot_head == None:
        need_snapshot_head = False
        for record in records:
            if len(record.snapshots) > 1:
                need_snapshot_head = True
        if need_snapshot_head:
            args.format_snapshot_head = 'monitored time: [<monitor start time>, <monitor end time>] (<monitor duration>)'
        else:
            args.format_snapshot_head = ''

    if args.total_sz_only:
        args.format_snapshot_head = ''
        args.format_region = ''
        args.format_snapshot_tail = '<total bytes>'

def sorted_regions(regions, sort_fields):
    for field in sort_fields:
        if field == 'address':
            regions = sorted(regions, key=lambda r: r.start)
        elif field == 'access_rate':
            regions = sorted(regions, key=lambda r: r.nr_accesses.percent)
        elif field == 'age':
            regions = sorted(regions, key=lambda r: r.age.usec)
        elif field == 'size':
            regions = sorted(regions, key=lambda r: r.size())
    return regions

def pr_records(args, records):
    if args.json:
        print(json.dumps([r.to_kvpairs(args.raw_number)
            for r in records], indent=4))
        exit(0)

    set_formats(args, records)
    mms = MinMaxOfRecords(records)

    for record in records:
        format_pr(args.format_record_head, args.min_chars_field, None, None,
                None, record, args.raw_number, mms)
        snapshots = record.snapshots

        for sidx, snapshot in enumerate(snapshots):
            format_pr(args.format_snapshot_head, args.min_chars_field, None,
                    None, snapshot, record, args.raw_number, mms)
            for r in snapshot.regions:
                r.nr_accesses.add_unset_unit(record.intervals)
                r.age.add_unset_unit(record.intervals)
            for idx, r in enumerate(
                    sorted_regions(snapshot.regions, args.sort_regions_by)):
                format_pr(args.format_region, args.min_chars_field, idx, r,
                        snapshot, record, args.raw_number, mms)
            format_pr(args.format_snapshot_tail, args.min_chars_field, None,
                    None, snapshot, record, args.raw_number, mms)

            if sidx < len(snapshots) - 1 and not args.total_sz_only:
                print('')
        format_pr(args.format_record_tail, args.min_chars_field, None, None,
                None, record, args.raw_number, mms)

def filter_by_pattern(record, access_pattern):
    sz_bytes = access_pattern.sz_bytes
    nr_acc = access_pattern.nr_acc_min_max
    age = access_pattern.age_min_max

    for snapshot in record.snapshots:
        filtered = []
        for region in snapshot.regions:
            sz = region.size()
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

def filter_by_addr(region, addr_ranges):
    regions = []
    for start, end in addr_ranges:
        # out of the range
        if region.end <= start or end <= region.start:
            continue
        # in the range
        if start <= region.start and region.end <= end:
            regions.append(copy.deepcopy(region))
            continue
        # overlap
        copied = copy.deepcopy(region)
        copied.start = max(start, region.start)
        copied.end = min(end, region.end)
        regions.append(copied)
    return regions

def filter_records_by_addr(records, addr_ranges):
    for record in records:
        for snapshot in record.snapshots:
            filtered_regions = []
            for region in snapshot.regions:
                filtered_regions += filter_by_addr(region, addr_ranges)
            snapshot.regions = filtered_regions
            snapshot.update_total_bytes()

def convert_addr_ranges_input(addr_ranges_input):
    try:
        ranges = [[_damo_fmt_str.text_to_bytes(start),
            _damo_fmt_str.text_to_bytes(end)]
            for start, end in addr_ranges_input]
    except Exception as e:
        return None, 'conversion to bytes failed (%s)' % e

    ranges.sort(key=lambda x: x[0])
    for idx, arange in enumerate(ranges):
        start, end = arange
        if start > end:
            return None, 'start > end (%s)' % arange
        if idx > 0 and ranges[idx - 1][1] > start:
            return None, 'overlapping range'
    return ranges, None

def set_argparser(parser):
    _damon_args.set_common_argparser(parser)

    # what to show
    parser.add_argument('--sz_region', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max size of regions (bytes)')
    parser.add_argument('--access_rate', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max access rate of regions (percent)')
    parser.add_argument('--age', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max age of regions (seconds)')
    parser.add_argument('--address', metavar=('<start>', '<end>'), nargs=2,
            action='append',
            help='address ranges to show for')

    parser.add_argument('--input_file', metavar='<file>',
            help='source of the access pattern to show')
    parser.add_argument('--tried_regions_of', nargs=3, type=int,
            action='append',
            metavar=('<kdamond idx>', '<context idx>', '<scheme idx>'),
            help='show tried regions of given schemes')

    # how to show

    # don't set default for record head and snapshot head because it depends on
    # given number of record and snapshots.  Decide those in set_formats().
    parser.add_argument('--format_record_head', metavar='<template>',
            help='record output head format')
    parser.add_argument('--format_record_tail', metavar='<template>',
            default='',
            help='record output tail format')
    parser.add_argument('--format_snapshot_head', metavar='<template>',
            help='snapshot output tail format')
    parser.add_argument('--format_snapshot_tail', metavar='<template>',
            default='total size: <total bytes>',
            help='snapshot output tail format')
    parser.add_argument('--format_region', metavar='<template>',
            default='<index> addr [<start address>, <end address>) (<region size>) access <access rate> age <age>',
            help='region output format')
    parser.add_argument('--min_chars_field', nargs=2,
            metavar=('<field name>', '<number>'), action='append',
            default=[['<index>', 3],
                ['<start address>', 12],['<end address>', 11],
                ['<region size>', 11], ['<access rate>', 5]],
            help='minimum character for each field')
    parser.add_argument('--total_sz_only', action='store_true',
            help='print only total size of the regions')
    parser.add_argument('--raw_number', action='store_true',
            help='use machine-friendly raw numbers')
    parser.add_argument('--json', action='store_true',
            help='print in json format')
    parser.add_argument('--sort_regions_by',
            choices=['address', 'access_rate', 'age', 'size'], nargs='+',
            default=['address'],
            help='fields to sort regions by')
    parser.add_argument('--dont_merge_regions', action='store_true',
            help='don\'t merge contiguous regions of same access pattern')

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
        err = 'assumed error'
        nr_tries = 0
        while err != None and nr_tries < 5:
            nr_tries += 1
            if args.tried_regions_of == None:
                records, err = _damon_result.get_snapshot_records(access_pattern,
                        args.total_sz_only, not args.dont_merge_regions)
            else:
                 records, err = _damon_result.get_snapshot_records_for_schemes(
                        args.tried_regions_of, args.total_sz_only,
                        not args.dont_merge_regions)
            if err != None:
                time.sleep(random.randrange(
                    2**(nr_tries - 1), 2**nr_tries) / 100)
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
    if args.address:
        ranges, err = convert_addr_ranges_input(args.address)
        if err:
            print('wrong --address input (%s)' % err)
            exit(1)
        filter_records_by_addr(records, ranges)

    for record in records:
        try:
            pr_records(args, records)
        except BrokenPipeError as e:
            # maybe user piped to 'less' like pager, and quit from it
            pass

if __name__ == '__main__':
    main()
