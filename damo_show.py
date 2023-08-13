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
        Formatter('<abs start time>',
            lambda record, raw:
            _dmo_fmt_str.format_ns(record.snapshots[0].start_time, raw),
            'absolute time of the start of the record'),
        Formatter('<duration>',
            lambda record, raw:
            _damo_fmt_str.format_time_ns(
                record.snapshots[-1].end_time - record.snapshots[0].start_time,
                raw),
            'duration of the record'),
        ]

snapshot_formatters = [
        Formatter('<total bytes>',
            lambda snapshot, record, raw, rbargs:
            _damo_fmt_str.format_sz(snapshot.total_bytes, raw),
            'total bytes of regions in the snapshot'),
        Formatter('<duration>',
            lambda snapshot, record, raw, rbargs: _damo_fmt_str.format_time_ns(
                snapshot.end_time - snapshot.start_time, raw),
            'access monitoring duration for the snapshot'),
        Formatter('<start time>',
            lambda snapshot, record, raw, rbargs: _damo_fmt_str.format_time_ns(
                snapshot.start_time - record.snapshots[0].start_time, raw),
            'access monitoring start time for the snapshot, relative to the record start time'),
        Formatter('<end time>',
            lambda snapshot, record, raw, rbargs: _damo_fmt_str.format_time_ns(
                snapshot.end_time - record.snapshots[0].start_time, raw),
            'access monitoring end time for the snapshot, relative to the record end time'),
        Formatter('<abs start time>',
            lambda snapshot, record, raw, rbargs:
            _damo_fmt_str.format_time_ns(snapshot.start_time, raw),
            'absolute access monitoring start time for the snapshot'),
        Formatter('<abs end time>',
            lambda snapshot, record, raw, rbargs:
            _damo_fmt_str.format_time_ns(snapshot.end_time, raw),
            'absolute access monitoring end time for the snapshot'),
        Formatter('<number of regions>',
            lambda snapshot, record, raw, rbargs:
            _damo_fmt_str.format_nr(len(snapshot.regions), raw),
            'the number of regions in the snapshot'),
        Formatter('<region box colors>',
            lambda snapshot, record, raw, rbargs:
            _damo_ascii_color.color_samples(rbargs.colorset),
            'available colors for the region box'),
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
        Formatter('<size>',
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
        Formatter('<age heat size box>',
            lambda index, region, raw, rbargs:
            rbargs.to_str(region, 'age', 'heat', 'size'),
            'box representing age, heat, and size of each region via length, color, and height'),
        Formatter('<box>',
            lambda index, region, raw, rbargs:
            rbargs.to_str(region, None, None, None),
            'user-customizable (via --region_box_*) box (age-heat-size by default)'),
        ]

def rescale(val, orig_scale_minmax, new_scale_minmax, logscale=True):
    '''Return a value in new scale

    Parameters
    ----------
    val : int, float
        The value to rescale
    orig_scale_minmax : list
        min/max values of original scale
    new_scale_minmax : list
        min/max values of new scale
    logscale : bool
        whether to use logscale (True) or linearscale (False)

    Returns
    -------
    float
        The rescaled value
    '''

    if logscale:
        log_val = math.log(val, 2) if val > 0 else 0
        log_minmax = [math.log(v, 2) if v > 0 else 0
                for v in orig_scale_minmax]
        val = log_val
        orig_scale_minmax = log_minmax
    orig_length = orig_scale_minmax[1] - orig_scale_minmax[0]
    new_length = new_scale_minmax[1] - new_scale_minmax[0]
    ratio = new_length / orig_length if orig_length > 0 else 1
    return (val - orig_scale_minmax[0]) * ratio + new_scale_minmax[0]

class ColoredBox:
    # original values and their min/max
    length_val = None
    length_val_minmaxs = None

    color_val = None
    color_val_minmaxs = None

    height_val = None
    height_val_minmaxs = None

    # final values to show
    length_minmaxs = None
    height_minmaxs = None
    colorset = None

    length_scale = None
    color_scale = None
    height_scale = None

    def __init__(self, length_val, length_val_minmaxs, length_minmaxs,
            color_val, color_val_minmaxs, colorset,
            height_val, height_val_minmaxs, height_minmaxs,
            length_color_height_scales=['log', 'linear', 'log']):
        self.length_val = length_val
        self.length_val_minmaxs = length_val_minmaxs
        self.length_minmaxs = length_minmaxs
        self.length_scale = length_color_height_scales[0]

        self.color_val = color_val
        self.color_val_minmaxs = color_val_minmaxs
        self.colorset = colorset
        self.color_scale = length_color_height_scales[1]

        self.height_val = height_val
        self.height_val_minmaxs = height_val_minmaxs
        self.height_minmaxs = height_minmaxs
        self.height_scale = length_color_height_scales[2]

    def __str__(self):
        length = int(rescale(self.length_val,
            self.length_val_minmaxs, self.length_minmaxs,
            self.length_scale == 'log'))

        if self.height_val != None:
            height = int(rescale(self.height_val,
                self.height_val_minmaxs, self.height_minmaxs,
                self.height_scale == 'log'))
        else:
            self.height_minmaxs = [1, 1]
            height = 1

        if type(self.color_val) == str:
            row = '%s' % (self.color_val * length)
        else:
            color_level = int(rescale(self.color_val,
                self.color_val_minmaxs, [0, 9],
                self.color_scale == 'log'))
            row = '%s' % _damo_ascii_color.colored(
                    ('%d' % color_level) * length, self.colorset, color_level)
        row = '|%s|' % row

        box = '\n'.join([row] * height)
        if self.height_minmaxs[1] > 1:
            box += '\n'
        return box

class SortedAccessPatterns:
    sz_regions = None
    access_rates_percent = None
    ages_us = None

    def __init__(self, records):
        self.sz_regions = []
        self.access_rates_percent = []
        self.ages_us = []

        for record in records:
            for snapshot in record.snapshots:
                for region in snapshot.regions:
                    self.sz_regions.append(region.size())

                    region.nr_accesses.add_unset_unit(record.intervals)
                    self.access_rates_percent.append(
                            region.nr_accesses.percent)

                    region.age.add_unset_unit(record.intervals)
                    self.ages_us.append(region.age.usec)
        self.sz_regions.sort()
        self.access_rates_percent.sort()
        self.ages_us.sort()

def nth_percentile(sorted_values, percentile):
    return sorted_values[min(
        int(percentile * 100 / len(sorted_vals)), len(sorted_vals) - 1)]

class RegionBoxArgs:
    sorted_access_patterns = None
    min_max_lengths = None
    min_max_heights = None
    colorset = None

    length_val_name = None
    color_val_name = None
    height_val_name = None

    # linear or log scales for length, color, and height
    length_color_height_scales = None

    def __init__(self, sorted_access_patterns, min_max_lengths,
            min_max_heights, colorset, length_val_name=None,
            color_val_name=None, height_val_name=None,
            length_color_height_scales=['log', 'linear', 'log']):
        self.sorted_access_patterns = sorted_access_patterns
        self.min_max_lengths = min_max_lengths
        self.min_max_heights = min_max_heights
        self.colorset = colorset
        self.length_val_name = length_val_name
        self.color_val_name = color_val_name
        self.height_val_name = height_val_name
        self.length_color_height_scales = length_color_height_scales

    def val_minmax(self, region, value_name):
        sorted_vals = self.sorted_access_patterns
        if value_name == 'size':
            return region.size(), [
                    sorted_vals.sz_regions[0], sorted_vals.sz_regions[-1]]
        elif value_name in ['heat', 'access_rate']:
            return region.nr_accesses.percent, [
                    sorted_vals.access_rates_percent[0],
                    sorted_vals.access_rates_percent[-1]]
        elif value_name == 'age':
            return region.age.usec, [sorted_vals.ages_us[0],
                    sorted_vals.ages_us[-1]]
        return None, None

    def to_str(self, region, length_val_name, color_val_name, height_val_name):
        if length_val_name == None:
            length_val_name = self.length_val_name
        if color_val_name == None:
            color_val_name = self.color_val_name
        if height_val_name == None:
            height_val_name = self.height_val_name

        if (length_val_name == None and color_val_name == None and
                height_val_name == None):
            length_val_name = 'age'
            color_val_name = 'heat'
            height_val_name = 'size'

        length_val, length_val_minmax = self.val_minmax(region,
                length_val_name)
        color_val, color_val_minmax = self.val_minmax(region, color_val_name)
        if color_val == None:
            color_val = '-'
        height_val, height_val_minmax = self.val_minmax(region,
                height_val_name)

        return '%s' % ColoredBox(length_val, length_val_minmax,
                self.min_max_lengths,
                color_val, color_val_minmax, self.colorset,
                height_val, height_val_minmax, self.min_max_heights,
                self.length_color_height_scales)

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

def format_pr(template, formatters, min_chars, index, region, snapshot, record,
        raw, region_box_args):
    if template == '':
        return
    for formatter in formatters:
        field_name = formatter.keyword
        if template.find(field_name) == -1:
            continue
        if formatters == record_formatters:
            txt = formatter.format_fn(record, raw)
        elif formatters == snapshot_formatters:
            txt = formatter.format_fn(snapshot, record, raw, region_box_args)
        elif formatters == region_formatters:
            txt = formatter.format_fn(index, region, raw, region_box_args)
        txt = apply_min_chars(min_chars, field_name, txt)
        template = template.replace(field_name, txt)
    template = template.replace('\\n', '\n')
    print(template)

def set_formats(args, records):
    if args.format_record_head == None:
        if len(records) > 1:
            args.format_record_head = 'kdamond <kdamond index> / context <context index> / scheme <scheme index> / target id <target id> / recorded for <duration> from <abs start time>'
        else:
            args.format_record_head = ''

    if args.format_snapshot_head == None:
        need_snapshot_head = False
        for record in records:
            if len(record.snapshots) > 1:
                need_snapshot_head = True
        if need_snapshot_head:
            args.format_snapshot_head = 'monitored time: [<start time>, <end time>] (<duration>)'
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
    sorted_access_patterns = SortedAccessPatterns(records)
    region_box_args = RegionBoxArgs(sorted_access_patterns,
            args.region_box_min_max_length, args.region_box_min_max_height,
            args.region_box_colorset,
            args.region_box_values[0], args.region_box_values[1],
            args.region_box_values[2], args.region_box_scales)

    for record in records:
        format_pr(args.format_record_head, record_formatters,
                args.min_chars_for, None, None, None, record, args.raw_number,
                region_box_args)
        snapshots = record.snapshots

        for sidx, snapshot in enumerate(snapshots):
            format_pr(args.format_snapshot_head, snapshot_formatters,
                    args.min_chars_for, None, None, snapshot, record,
                    args.raw_number, region_box_args)
            for r in snapshot.regions:
                r.nr_accesses.add_unset_unit(record.intervals)
                r.age.add_unset_unit(record.intervals)
            for idx, r in enumerate(
                    sorted_regions(snapshot.regions, args.sort_regions_by)):
                format_pr(args.format_region, region_formatters,
                        args.min_chars_for, idx, r, snapshot, record,
                        args.raw_number, region_box_args)
            format_pr(args.format_snapshot_tail, snapshot_formatters,
                    args.min_chars_for, None, None, snapshot, record,
                    args.raw_number, region_box_args)

            if sidx < len(snapshots) - 1 and not args.total_sz_only:
                print('')
        format_pr(args.format_record_tail, record_formatters,
                args.min_chars_for, None, None, None, record, args.raw_number,
                region_box_args)

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
            help='min/max size of regions (bytes) to show')
    parser.add_argument('--access_rate', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max access rate of regions (percent) to show')
    parser.add_argument('--age', metavar=('<min>', '<max>'), nargs=2,
            default=['min', 'max'],
            help='min/max age of regions (seconds) to show')
    parser.add_argument('--address', metavar=('<start>', '<end>'), nargs=2,
            action='append',
            help='address ranges to show')

    parser.add_argument('--input_file', metavar='<file>',
            help='source of the access pattern to show')
    parser.add_argument('--tried_regions_of', nargs=3, type=int,
            action='append',
            metavar=('<kdamond idx>', '<context idx>', '<scheme idx>'),
            help='show tried regions of given schemes')

    # how to show
    parser.add_argument('--sort_regions_by',
            choices=['address', 'access_rate', 'age', 'size'], nargs='+',
            default=['address'],
            help='fields to sort regions by')
    parser.add_argument('--dont_merge_regions', action='store_true',
            help='don\'t merge contiguous regions of same access pattern')

    # don't set default for record head and snapshot head because it depends on
    # given number of record and snapshots.  Decide those in set_formats().
    parser.add_argument('--format_record_head', metavar='<template>',
            help='output format to show at the beginning of each record')
    parser.add_argument('--format_record_tail', metavar='<template>',
            default='',
            help='output format to show at the end of each record')
    parser.add_argument('--ls_record_format_keywords', action='store_true',
            help='list available record format keywords')
    parser.add_argument('--format_snapshot_head', metavar='<template>',
            help='output format to show at the beginning of each snapshot')
    parser.add_argument('--format_snapshot_tail', metavar='<template>',
            default='total size: <total bytes>',
            help='output format to show at the end of each snapshot')
    parser.add_argument('--ls_snapshot_format_keywords', action='store_true',
            help='list available snapshot format keywords')
    parser.add_argument('--format_region', metavar='<template>',
            default='<index> addr [<start address>, <end address>) (<size>) access <access rate> age <age>',
            help='output format to show for each memory region')
    parser.add_argument('--ls_region_format_keywords', action='store_true',
            help='list available region format keywords')
    parser.add_argument('--region_box_values',
            choices=['size', 'access_rate', 'age', 'none'], nargs=3,
            default=['none', 'none', 'none'],
            help='values to show via the <box>\'s length, color, and height')
    parser.add_argument('--region_box_min_max_length', nargs=2, type=int,
            metavar=('<min>', '<max>'), default=[1, 30],
            help='minimum and maximum number of the region box\' length')
    parser.add_argument('--region_box_min_max_height', nargs=2, type=int,
            metavar=('<min>', '<max>'), default=[1, 5],
            help='minimum and maximum number of region box\' height')
    parser.add_argument('--region_box_colorset', default='gray',
            choices=['gray', 'flame', 'emotion'],
            help='colorset to use for region box')
    parser.add_argument('--region_box_scales', choices=['linear', 'log'],
            nargs=3, default=['log', 'linear', 'log'],
            help='scale of region box\' length, color, and height')
    parser.add_argument('--min_chars_for', nargs=2,
            metavar=('<keyword>', '<number>'), action='append',
            default=[['<index>', 3],
                ['<start address>', 12],['<end address>', 11],
                ['<size>', 11], ['<access rate>', 5]],
            help='minimum character for each keyword of the format')
    parser.add_argument('--total_sz_only', action='store_true',
            help='print only total size of the regions for each snapshot')
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
