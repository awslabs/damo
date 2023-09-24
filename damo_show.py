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
            _damo_fmt_str.format_time_ns(record.snapshots[0].start_time, raw),
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
        Formatter('<region box description>',
            lambda snapshot, record, raw, rbargs:
            rbargs.description_msg(raw),
            'description about region box (what and how it represents)'),
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
        Formatter('<box>',
            lambda index, region, raw, rbargs:
            rbargs.to_str(region),
            'user-customizable (via --region_box_*) box (age/access_rate/size by default)'),
        ]

default_record_head_format = 'kdamond <kdamond index> / context <context index> / scheme <scheme index> / target id <target id> / recorded for <duration> from <abs start time>'
default_snapshot_head_format = 'monitored time: [<start time>, <end time>] (<duration>)'
default_region_format = '<index> addr [<start address>, <end address>) (<size>) access <access rate> age <age>'

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

class BoxValue:
    val = None
    val_min_max = None      # list of min/max
    display_min_max = None  # list of min/max
    display_logscale = None # bool

    def __init__(self, val, val_min_max, display_min_max, display_logscale):
        self.val = val
        self.val_min_max = val_min_max
        self.display_min_max = display_min_max
        self.display_logscale = display_logscale

    def display_value(self):
        return rescale(self.val, self.val_min_max, self.display_min_max,
                self.display_logscale)

class ColoredBox:
    # BoxValue
    length = None
    color = None
    height = None

    colorset = None

    def __init__(self, length, color, colorset, height):
        self.length = length
        self.color = color
        self.colorset = colorset
        self.height = height

    def __str__(self):
        length = int(self.length.display_value())

        if self.height.val != None:
            height = int(self.height.display_value())
        else:
            self.height.display_min, self.height.display_max = [1, 1]
            height = 1

        if type(self.color.val) == str:
            row = '%s' % (self.color.val * length)
        else:
            color_level = int(self.color.display_value())
            row = '%s' % _damo_ascii_color.colored(
                    ('%d' % color_level) * length, self.colorset, color_level)
        row = '|%s|' % row

        box = '\n'.join([row] * height)
        if self.height.display_min_max[1] > 1:
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

class RegionBoxValArgs:
    value_name = None
    display_min_max = None
    display_logscale = None

    def __init__(self, value_name, display_min_max, display_logscale):
        self.value_name = value_name
        self.display_min_max = display_min_max
        self.display_logscale = display_logscale

class RegionBoxArgs:
    sorted_access_patterns = None
    length = None
    color = None
    colorset = None
    height = None

    def __init__(self, sorted_access_patterns, length, color, colorset,
            height):
        self.sorted_access_patterns = sorted_access_patterns
        self.length = length
        self.color = color
        self.colorset = colorset
        self.height = height

    def minmax(self, value_name):
        if value_name == 'size':
            sorted_vals = self.sorted_access_patterns.sz_regions
        elif value_name == 'access_rate':
            sorted_vals = self.sorted_access_patterns.access_rates_percent
        elif value_name == 'age':
            sorted_vals = self.sorted_access_patterns.ages_us
        return sorted_vals[0], sorted_vals[-1]

    def val_minmax(self, region, value_name):
        minval, maxval = self.minmax(value_name)
        if value_name == 'size':
            return region.size(), [minval, maxval]
        elif value_name == 'access_rate':
            return region.nr_accesses.percent, [minval, maxval]
        elif value_name == 'age':
            return region.age.usec, [minval, maxval]
        return None, None

    def to_str(self, region):
        length_val, length_val_minmax = self.val_minmax(region,
                self.length.value_name)
        color_val, color_val_minmax = self.val_minmax(region,
                self.color.value_name)
        if color_val == None:
            color_val = '-'
        height_val, height_val_minmax = self.val_minmax(region,
                self.height.value_name)

        return '%s' % ColoredBox(
                BoxValue(length_val, length_val_minmax,
                    self.length.display_min_max, self.length.display_logscale),
                BoxValue(color_val, color_val_minmax, [0, 9],
                    self.color.display_logscale),
                self.colorset,
                BoxValue(height_val, height_val_minmax,
                    self.height.display_min_max, self.height.display_logscale))

    def format_min_max(self, minval, maxval, value_name, raw):
        if value_name == 'size':
            return '[%s, %s]' % (_damo_fmt_str.format_sz(minval, raw),
                    _damo_fmt_str.format_sz(maxval, raw))
        if value_name == 'age':
            return '[%s, %s] ' % (_damo_fmt_str.format_time_us(minval, raw),
                    _damo_fmt_str.format_time_us(maxval, raw))
        if value_name == 'access_rate':
            return '[%s, %s]' % (_damo_fmt_str.format_percent(minval, raw),
                    _damo_fmt_str.format_percent(maxval, raw))

    def description_msg(self, raw):
        lines = []
        minval, maxval = self.minmax(self.length.value_name)
        lines.append('# length: %s (represents %s with [%d, %d] columns in %s)'
                % (self.length.value_name,
                    self.format_min_max(minval, maxval,
                        self.length.value_name, raw),
                    self.length.display_min_max[0],
                    self.length.display_min_max[1],
                    'logscale'
                    if self.length.display_logscale else 'linearscale'))

        minval, maxval = self.minmax(self.color.value_name)
        lines.append('# color: %s (represents %s with [%d, %d] number and color (%s) in %s)'
                % (self.color.value_name,
                    self.format_min_max(minval, maxval,
                        self.color.value_name, raw),
                    self.color.display_min_max[0],
                    self.color.display_min_max[1],
                    _damo_ascii_color.color_samples(self.colorset),
                    'logscale'
                    if self.color.display_logscale else 'linearscale'))

        minval, maxval = self.minmax(self.height.value_name)
        lines.append('# height: %s (represents %s with [%d, %d] rows in %s)'
                % (self.height.value_name,
                    self.format_min_max(minval, maxval,
                        self.height.value_name, raw),
                    self.height.display_min_max[0],
                    self.height.display_min_max[1],
                    'logscale'
                    if self.height.display_logscale else 'linearscale'))
        return '\n'.join(lines)

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

def format_template(template, formatters, min_chars, index, region, snapshot,
        record, raw, region_box_args):
    if template == '':
        return
    for formatter in formatters:
        if template.find(formatter.keyword) == -1:
            continue
        if formatters == record_formatters:
            txt = formatter.format_fn(record, raw)
        elif formatters == snapshot_formatters:
            txt = formatter.format_fn(snapshot, record, raw, region_box_args)
        elif formatters == region_formatters:
            txt = formatter.format_fn(index, region, raw, region_box_args)
        txt = apply_min_chars(min_chars, formatter.keyword, txt)
        template = template.replace(formatter.keyword, txt)
    template = template.replace('\\n', '\n')
    return template

def format_pr(template, formatters, min_chars, index, region, snapshot, record,
        raw, region_box_args):
    if template == '':
        return
    print(format_template(template, formatters, min_chars, index, region,
        snapshot, record, raw, region_box_args))

def set_formats(args, records):
    if args.format_record_head == None:
        if len(records) > 1:
            args.format_record_head = default_record_head_format
        else:
            args.format_record_head = ''

    if args.format_snapshot_head == None:
        need_snapshot_head = False
        for record in records:
            if len(record.snapshots) > 1:
                need_snapshot_head = True
                break
        if need_snapshot_head:
            args.format_snapshot_head = default_snapshot_head_format
        else:
            args.format_snapshot_head = ''

    if args.total_sz_only:
        args.format_snapshot_head = ''
        args.format_region = ''
        args.format_snapshot_tail = '<total bytes>'

    if args.region_box:
        args.format_region = '<box>%s' % default_region_format
        if args.format_snapshot_tail.find('<region box description>') == -1:
            args.format_snapshot_tail = ('%s\n<region box description>' %
                    args.format_record_tail)

def sorted_regions(regions, sort_fields, sort_dsc_keys):
    for field in sort_fields:
        if field == 'address':
            dsc = sort_dsc_keys != None and ('all' in sort_dsc_keys or
                    'address' in sort_dsc_keys)
            regions = sorted(regions, key=lambda r: r.start, reverse=dsc)
        elif field == 'access_rate':
            dsc = sort_dsc_keys != None and ('all' in sort_dsc_keys or
                    'access_rate' in sort_dsc_keys)
            regions = sorted(regions, key=lambda r: r.nr_accesses.percent,
                    reverse=dsc)
        elif field == 'age':
            dsc = sort_dsc_keys != None and ('all' in sort_dsc_keys or
                    'age' in sort_dsc_keys)
            regions = sorted(regions, key=lambda r: r.age.usec,
                    reverse=dsc)
        elif field == 'size':
            dsc = sort_dsc_keys != None and ('all' in sort_dsc_keys or
                    'size' in sort_dsc_keys)
            regions = sorted(regions, key=lambda r: r.size(), reverse=dsc)
    return regions

def pr_records(args, records):
    if args.json:
        print(json.dumps([r.to_kvpairs(args.raw_number)
            for r in records], indent=4))
        exit(0)

    set_formats(args, records)
    sorted_access_patterns = SortedAccessPatterns(records)
    region_box_args = RegionBoxArgs(sorted_access_patterns,
            RegionBoxValArgs(args.region_box_values[0],
                args.region_box_min_max_length,
                args.region_box_scales[0] == 'log'),
            RegionBoxValArgs(args.region_box_values[1],
                [0, 9], args.region_box_scales[1] == 'log'),
            args.region_box_colorset,
            RegionBoxValArgs(args.region_box_values[2],
                args.region_box_min_max_height,
                args.region_box_scales[2] == 'log'))

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
                    sorted_regions(snapshot.regions, args.sort_regions_by,
                        args.sort_regions_dsc)):
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
    parser.add_argument('--sort_regions_dsc',
            choices=['address', 'access_rate', 'age', 'size', 'all'],
            nargs='+',
            help='sort regions in descending order for the given keys')
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
            default=default_region_format,
            help='output format to show for each memory region')
    parser.add_argument('--ls_region_format_keywords', action='store_true',
            help='list available region format keywords')
    parser.add_argument('--region_box_values',
            choices=['size', 'access_rate', 'age', 'none'], nargs=3,
            default=['age', 'access_rate', 'size'],
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
    parser.add_argument('--region_box', action='store_true',
            help='show region access pattern as a box')
    parser.add_argument('--total_sz_only', action='store_true',
            help='print only total size of the regions for each snapshot')
    parser.add_argument('--raw_number', action='store_true',
            help='use machine-friendly raw numbers')
    parser.add_argument('--json', action='store_true',
            help='print in json format')

    parser.description = 'Show DAMON-monitored access pattern'
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
        if not _damon.feature_supported('schemes_tried_regions'):
            print('damos tried regions feature not supported')
            exit(0)
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
