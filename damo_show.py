# SPDX-License-Identifier: GPL-2.0

import argparse
import collections
import copy
import json
import math
import os
import random
import time

import _damo_ascii_color
import _damo_fmt_str
import _damon
import _damon_args
import _damon_result

class Formatter:
    keyword = None
    format_fn = None
    help_msg = None

    def __init__(self, keyword, format_fn, help_msg):
            self.keyword = keyword
            self.format_fn = format_fn
            self.help_msg = help_msg

    def __str__(self):
        return '%s\n%s' % (self.keyword, self.help_msg)

record_formatters = [
        Formatter('<kdamond index>',
            lambda record, raw: '%s' % record.kdamond_idx,
            'index of the record\'s kdamond'),
        Formatter('<context index>',
            lambda record, raw: '%s' % record.context_idx,
            'index of the record\'s DAMON context'),
        Formatter('<scheme index>',
            lambda record, raw: '%s' % record.scheme_idx,
            'index of the record\'s DAMOS scheme'),
        Formatter('<target id>',
            lambda record, raw: '%s' % record.target_id,
            'index of the record\'s DAMON target'),
        Formatter('<record start abs time>',
            lambda record, raw:
            _dmo_fmt_str.format_ns(record.snapshots[0].start_time, raw),
            'absolute time of the start of the record'),
        Formatter('<record duration>',
            lambda record, raw:
            _damo_fmt_str.format_time_ns(
                record.snapshots[-1].end_time - record.snapshots[0].start_time,
                raw),
            'duration of the record'),
        ]

snapshot_formatters = [
        Formatter('<total bytes>',
            lambda snapshot, record, raw:
            _damo_fmt_str.format_sz(snapshot.total_bytes, raw),
            'total bytes of regions in the snapshot'),
        Formatter('<monitor duration>',
            lambda snapshot, record, raw: _damo_fmt_str.format_time_ns(
                snapshot.end_time - snapshot.start_time, raw),
            'access monitoring duration for the snapshot'),
        Formatter('<monitor start time>',
            lambda snapshot, record, raw: _damo_fmt_str.format_time_ns(
                snapshot.start_time - record.snapshots[0].start_time, raw),
            'access monitoring start time for the snapshot, relative to the record start time'),
        Formatter('<monitor end time>',
            lambda snapshot, record, raw: _damo_fmt_str.format_time_ns(
                snapshot.end_time - record.snapshots[0].start_time, raw),
            'access monitoring end time for the snapshot, relative to the record end time'),
        Formatter('<monitor start abs time>',
            lambda snapshot, record, raw:
            _damo_fmt_str.format_time_ns(snapshot.start_time, raw),
            'absolute access monitoring start time for the snapshot'),
        Formatter('<monitor end abs time>',
            lambda snapshot, record, raw:
            _damo_fmt_str.format_time_ns(snapshot.end_time, raw),
            'absolute access monitoring end time for the snapshot'),
        Formatter('<number of regions>',
            lambda snapshot, record, raw:
            _damo_fmt_str.format_nr(len(snapshot.regions), raw),
            'the number of regions in the snapshot'),
        ]

region_formatters = [
        Formatter('<index>',
            lambda index, region, raw, rbargs:
            _damo_fmt_str.format_nr(index, raw),
            'index of the region in the regions of the snapshot'),
        Formatter('<start address>',
            lambda index, region, raw, rbargs:
            _damo_fmt_str.format_sz(region.start, raw),
            'start address of the region'),
        Formatter('<end address>',
            lambda index, region, raw, rbargs:
            _damo_fmt_str.format_sz(region.end, raw),
            'end address of the region'),
        Formatter('<region size>',
            lambda index, region, raw, rbargs:
            _damo_fmt_str.format_sz(region.size(), raw),
            'size of the region'),
        Formatter('<access rate>',
            lambda index, region, raw, rbargs:
            _damo_fmt_str.format_percent(region.nr_accesses.percent, raw),
            'monitored access rate of the region'),
        Formatter('<age>',
            lambda index, region, raw, rbargs:
            _damo_fmt_str.format_time_us(region.age.usec, raw),
            'how long the access pattern of the region has maintained'),
        Formatter('<size bar>',
            lambda index, region, raw, rbargs:
            rbargs.to_str(region, 'size', None, None),
            'character box representing relative size of the region'),
        Formatter('<size heat bar>',
            lambda index, region, raw, rbargs:
            rbargs.to_str(region, 'size', 'heat', None),
           'character box representing relative size and access frequency of the region'),
        Formatter('<age heat bar>',
            lambda index, region, raw, rbargs:
            rbargs.to_str(region, 'age', 'heat', None),
            'character box represeting relative age and access frequency of the region'),
        Formatter('<size heat age box>',
            lambda index, region, raw, rbargs:
            rbargs.to_str(region, 'size', 'heat', 'age'),
            'character box representing relative size, access frequency, and the age of the region'),
        Formatter('<box>',
            lambda index, region, raw, rbargs:
            rbargs.to_str(region, None, None, None),
            'user-customizable (via --region_box_*) box (size-heat-age by default)'),
        ]

formatters = {
        'record': record_formatters,
        'snapshot': snapshot_formatters,
        'region': region_formatters
        }

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
    ratio = new_length / orig_length if orig_length > 0 else 1
    return (val - orig_scale_minmax[0]) * ratio + new_scale_minmax[0]

def rescale_val_logscale(val, orig_scale_minmax, new_scale_minmax):
    '''Return a value in new scale, in logscale

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
    log_val = math.log(val, 2) if val > 0 else 0
    log_minmax = [math.log(v, 2) if v > 0 else 0 for v in orig_scale_minmax]
    return rescale_val(log_val, log_minmax, new_scale_minmax)

class ColoredBox:
    column_val = None
    column_val_minmaxs = None

    color_val = None
    color_val_minmaxs = None
    colorset = None

    row_val = None
    row_val_minmaxs = None

    nr_columns_minmaxs = None
    nr_rows_minmaxs = None

    def __init__(self, column_val, column_val_minmaxs, nr_columns_minmaxs,
            color_val, color_val_minmaxs, colorset,
            row_val, row_val_minmaxs, nr_rows_minmaxs):
        self.column_val = column_val
        self.column_val_minmaxs = column_val_minmaxs
        self.nr_columns_minmaxs = nr_columns_minmaxs

        self.color_val = color_val
        self.color_val_minmaxs = color_val_minmaxs
        self.colorset = colorset

        self.row_val = row_val
        self.row_val_minmaxs = row_val_minmaxs
        self.nr_rows_minmaxs = nr_rows_minmaxs

    def __str__(self):
        nr_cols = int(rescale_val_logscale(self.column_val,
            self.column_val_minmaxs, self.nr_columns_minmaxs))

        if self.row_val != None:
            nr_rows = int(rescale_val_logscale(self.row_val,
                self.row_val_minmaxs, self.nr_rows_minmaxs))
        else:
            nr_rows = 1

        if type(self.color_val) == str:
            row = '<%s>' % (self.color_val * nr_cols)
        else:
            color_level = int(rescale_val(self.color_val,
                self.color_val_minmaxs, [0, 9]))
            row = '<%s>' % _damo_ascii_color.colored(
                    ('%d' % color_level) * nr_cols, self.colorset, color_level)

        rows = '\n'.join([row] * nr_rows)
        if nr_rows > 1:
            rows += '\n'
        return rows

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

class RegionBoxArgs:
    record_minmaxs = None
    min_max_cols = None
    min_max_rows = None
    colorset = None

    col_val_name = None
    color_val_name = None
    row_val_name = None

    def __init__(self, record_minmaxs, min_max_cols, min_max_rows, colorset,
            col_val_name=None, color_val_name=None, row_val_name=None):
        self.record_minmaxs = record_minmaxs
        self.min_max_cols = min_max_cols
        self.min_max_rows = min_max_rows
        self.colorset = colorset
        self.col_val_name = col_val_name
        self.color_val_name = color_val_name
        self.row_val_name = row_val_name

    def val_minmax(self, region, value_name):
        mms = self.record_minmaxs
        if value_name == 'size':
            return region.size(), [mms.min_sz_region, mms.max_sz_region]
        elif value_name in ['heat', 'access_rate']:
            return region.nr_accesses.percent, [
                    mms.min_access_rate_percent, mms.max_access_rate_percent]
        elif value_name == 'age':
            return region.age.usec, [mms.min_age_us, mms.max_age_us]
        return None, None

    def to_str(self, region, col_val_name, color_val_name, row_val_name):
        if col_val_name == None:
            col_val_name = self.col_val_name
        if color_val_name == None:
            color_val_name = self.color_val_name
        if row_val_name == None:
            row_val_name = self.row_val_name

        if (col_val_name == None and color_val_name == None and
                row_val_name == None):
            col_val_name = 'size'
            color_val_name = 'heat'
            row_val_name = 'age'

        cval, cval_minmax = self.val_minmax(region, col_val_name)
        clval, clval_minmax = self.val_minmax(region, color_val_name)
        if clval == None:
            clval = '-'
        rval, rval_minmax = self.val_minmax(region, row_val_name)
        return '%s' % ColoredBox(cval, cval_minmax, self.min_max_cols,
                clval, clval_minmax, self.colorset,
                rval, rval_minmax, self.min_max_rows)

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

def format_pr(template, min_chars, index, region, snapshot, record, raw, mms,
        region_box_args):
    if template == '':
        return
    for category, category_formatters in formatters.items():
        for formatter in category_formatters:
            field_name = formatter.keyword
            if template.find(field_name) == -1:
                continue
            if category == 'record':
                txt = formatter.format_fn(record, raw)
            elif category == 'snapshot':
                txt = formatter.format_fn(snapshot, record, raw)
            elif category == 'region':
                txt = formatter.format_fn(index, region, raw, region_box_args)
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
    region_box_args = RegionBoxArgs(mms, args.region_box_min_max_cols,
            args.region_box_min_max_rows, args.region_box_colorset,
            args.region_box_values[0], args.region_box_values[1],
            args.region_box_values[2])

    for record in records:
        format_pr(args.format_record_head, args.min_chars_field, None, None,
                None, record, args.raw_number, mms, region_box_args)
        snapshots = record.snapshots

        for sidx, snapshot in enumerate(snapshots):
            format_pr(args.format_snapshot_head, args.min_chars_field, None,
                    None, snapshot, record, args.raw_number, mms,
                    region_box_args)
            for r in snapshot.regions:
                r.nr_accesses.add_unset_unit(record.intervals)
                r.age.add_unset_unit(record.intervals)
            for idx, r in enumerate(
                    sorted_regions(snapshot.regions, args.sort_regions_by)):
                format_pr(args.format_region, args.min_chars_field, idx, r,
                        snapshot, record, args.raw_number, mms,
                        region_box_args)
            format_pr(args.format_snapshot_tail, args.min_chars_field, None,
                    None, snapshot, record, args.raw_number, mms,
                    region_box_args)

            if sidx < len(snapshots) - 1 and not args.total_sz_only:
                print('')
        format_pr(args.format_record_tail, args.min_chars_field, None, None,
                None, record, args.raw_number, mms, region_box_args)

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
    parser.add_argument('--ls_record_format_keywords', action='store_true',
            help='list available record format keywords')
    parser.add_argument('--format_snapshot_head', metavar='<template>',
            help='snapshot output tail format')
    parser.add_argument('--format_snapshot_tail', metavar='<template>',
            default='total size: <total bytes>',
            help='snapshot output tail format')
    parser.add_argument('--ls_snapshot_format_keywords', action='store_true',
            help='list available snapshot format keywords')
    parser.add_argument('--format_region', metavar='<template>',
            default='<index> addr [<start address>, <end address>) (<region size>) access <access rate> age <age>',
            help='region output format')
    parser.add_argument('--ls_region_format_keywords', action='store_true',
            help='list available region format keywords')
    parser.add_argument('--region_box_values',
            choices=['size', 'access_rate', 'age', 'none'], nargs=3,
            default=['none', 'none', 'none'],
            help='values to show via the box\'s length, color, and height')
    parser.add_argument('--region_box_min_max_cols', nargs=2, type=int,
            metavar=('<min>', '<max>'), default=[1, 30],
            help='minimum and maximum number of columns for region box')
    parser.add_argument('--region_box_min_max_rows', nargs=2, type=int,
            metavar=('<min>', '<max>'), default=[1, 5],
            help='minimum and maximum number of rows for region box')
    parser.add_argument('--region_box_colorset', default='gray',
            choices=['gray', 'flame', 'emotion'],
            help='colorset to use for region box')
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

    args.region_box_values = [v if v != 'none' else None
            for v in args.region_box_values]

    access_pattern = _damon.DamosAccessPattern(args.sz_region,
            args.access_rate, _damon.unit_percent, args.age * 1000000,
            _damon.unit_usec)

    if args.ls_record_format_keywords:
        print('\n\n'.join(['%s' % f for f in record_formatters]))
        return
    if args.ls_snapshot_format_keywords:
        print('\n\n'.join(['%s' % f for f in snapshot_formatters]))
        return
    if args.ls_region_format_keywords:
        print('\n\n'.join(['%s' % f for f in region_formatters]))
        return

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
