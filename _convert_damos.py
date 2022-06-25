#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Change human readable data access monitoring-based operation schemes to the low
level input for the '<debugfs>/damon/schemes' file.  Below is an example of the
schemes written in the human readable format:

    # format is:
    # <min/max size> <min/max frequency (0-100)> <min/max age> <action>
    #
    # B/K/M/G/T for Bytes/KiB/MiB/GiB/TiB
    # us/ms/s/m/h/d for micro-seconds/milli-seconds/seconds/minutes/hours/days
    # 'min/max' for possible min/max value.

    # if a region keeps a high access frequency for >=100ms, put the region on
    # the head of the LRU list (call madvise() with MADV_WILLNEED).
    min    max      80      max     100ms   max willneed

    # if a region keeps a low access frequency for >=200ms and <=one hour, put
    # the region on the tail of the LRU list (call madvise() with MADV_COLD).
    min     max     10      20      200ms   1h  cold

    # if a region keeps a very low access frequency for >=60 seconds, swap out
    # the region immediately (call madvise() with MADV_PAGEOUT).
    min     max     0       10      60s     max pageout

    # if a region of a size >=2MiB keeps a very high access frequency for
    # >=100ms, let the region to use huge pages (call madvise() with
    # MADV_HUGEPAGE).
    2M      max     90      100     100ms   max hugepage

    # If a regions of a size >=2MiB keeps small access frequency for >=100ms,
    # avoid the region using huge pages (call madvise() with MADV_NOHUGEPAGE).
    2M      max     0       25      100ms   max nohugepage
"""

import argparse
import os
import platform

import _damon

uint_max = 2**32 - 1
ulong_max = 2**64 - 1
if platform.architecture()[0] != '64bit':
    ulong_max = 2**32 - 1

unit_to_bytes = {'B': 1, 'K': 1024, 'M': 1024 * 1024, 'G': 1024 * 1024 * 1024,
        'T': 1024 * 1024 * 1024 * 1024}

def text_to_bytes(txt):
    if txt == 'min':
        return 0
    if txt == 'max':
        return ulong_max

    unit = txt[-1]
    number = float(txt[:-1])
    return int(number * unit_to_bytes[unit])

unit_to_usecs = {'us': 1, 'ms': 1000, 's': 1000 * 1000, 'm': 60 * 1000 * 1000,
        'h': 60 * 60 * 1000 * 1000, 'd': 24 * 60 * 60 * 1000 * 1000}

def text_to_us(txt):
    if txt == 'min':
        return 0
    if txt == 'max':
        return uint_max

    unit = txt[-2:]
    if unit in ['us', 'ms']:
        number = float(txt[:-2])
    else:
        unit = txt[-1]
        number = float(txt[:-1])
    return number * unit_to_usecs[unit]

def text_to_ms(txt):
    return int(text_to_us(txt) / 1000)

damos_action_to_int = {'DAMOS_WILLNEED': 0, 'DAMOS_COLD': 1,
        'DAMOS_PAGEOUT': 2, 'DAMOS_HUGEPAGE': 3, 'DAMOS_NOHUGEPAGE': 4,
        'DAMOS_STAT': 5, 'DAMOS_LRU_PRIO': 6, 'DAMOS_LRU_DEPRIO': 7}

def text_to_nr_accesses(txt, max_nr_accesses):
    if txt == 'min':
        return 0
    if txt == 'max':
        return max_nr_accesses

    return int(float(txt) * max_nr_accesses / 100)

def text_percent_to_nr_accesses_permil(txt):
    if txt == 'min':
        return 0
    if txt == 'max':
        return 1000
    return float(txt) * 10

damos_wmark_metric_to_int = {'NONE': 0, 'FREE_MEM_RATE': 1}

def text_to_damos_wmark_metric(txt):
    return damos_wmark_metric_to_int[txt.upper()]

def damo_scheme_to_damos(line, scheme_version):
    fields = line.split()
    expected_lengths = [7, 9, 12, 17, 18]
    if not len(fields) in expected_lengths:
        print('expected %s fields, but \'%s\'' % (expected_lengths, line))
        exit(1)

    try:
        min_sz = text_to_bytes(fields[0])
        max_sz = text_to_bytes(fields[1])
        min_nr_accesses = text_percent_to_nr_accesses_permil(fields[2])
        max_nr_accesses = text_percent_to_nr_accesses_permil(fields[3])
        min_age_us = text_to_us(fields[4])
        max_age_us = text_to_us(fields[5])
        action_txt = 'DAMOS_' + fields[6].upper()
        action = damos_action_to_int[action_txt]
        quota_ms = 0
        quota_sz = 0
        window_ms = ulong_max
        weight_sz = 0
        weight_nr_accesses = 0
        weight_age = 0
        wmarks_metric = text_to_damos_wmark_metric('none')
        wmarks_interval = 0
        wmarks_high = 0
        wmarks_mid = 0
        wmarks_low = 0
        if len(fields) <= 17:
            if len(fields) >= 9:
                quota_sz = text_to_bytes(fields[7])
                window_ms = text_to_ms(fields[8])
            if len(fields) >= 12:
                weight_sz = int(fields[9])
                weight_nr_accesses = int(fields[10])
                weight_age = int(fields[11])
            if len(fields) == 17:
                wmarks_metric = text_to_damos_wmark_metric(fields[12])
                wmarks_interval = text_to_us(fields[13])
                wmarks_high = int(fields[14])
                wmarks_mid = int(fields[15])
                wmarks_low = int(fields[16])
        elif len(fields) == 18:
            quota_ms = text_to_ms(fields[7])
            quota_sz = text_to_bytes(fields[8])
            window_ms = text_to_ms(fields[9])
            weight_sz = int(fields[10])
            weight_nr_accesses = int(fields[11])
            weight_age = int(fields[12])
            wmarks_metric = text_to_damos_wmark_metric(fields[13])
            wmarks_interval = text_to_us(fields[14])
            wmarks_high = int(fields[15])
            wmarks_mid = int(fields[16])
            wmarks_low = int(fields[17])

    except:
        print('wrong input field')
        raise

    return _damon.Damos(_damon.DamosAccessPattern(min_sz, max_sz,
        min_nr_accesses, max_nr_accesses, min_age_us, max_age_us),
        action_txt,
        _damon.DamosQuota(quota_ms, quota_sz, window_ms, weight_sz,
            weight_nr_accesses, weight_age),
        _damon.DamosWatermarks(wmarks_metric, wmarks_interval, wmarks_high,
            wmarks_mid, wmarks_low))

def damos_to_debugfs_input(damos, sample_interval, aggr_interval,
        scheme_version):
    pattern = damos.access_pattern
    quotas = damos.quotas
    watermarks = damos.watermarks

    max_nr_accesses = aggr_interval / sample_interval
    v0_scheme = '%d\t%d\t%d\t%d\t%d\t%d\t%d' % (
            pattern.min_sz_bytes, pattern.max_sz_bytes,
            int(pattern.min_nr_accesses_permil * max_nr_accesses / 1000),
            int(pattern.max_nr_accesses_permil * max_nr_accesses / 1000),
            pattern.min_age_us / aggr_interval,
            pattern.max_age_us / aggr_interval,
            damos_action_to_int[damos.action])
    v1_scheme = '%s\t%d\t%d' % (v0_scheme,
            quotas.sz_bytes, quotas.reset_interval_ms)
    v2_scheme = '%s\t%d\t%d\t%d' % (v1_scheme,
            quotas.weight_sz_permil, quotas.weight_nr_accesses_permil,
            quotas.weight_age_permil)
    v3_scheme = '%s\t%d\t%d\t%d\t%d\t%d' % (v2_scheme,
            watermarks.metric, watermarks.interval_us, watermarks.high_permil,
            watermarks.mid_permil, watermarks.low_permil)
    v4_scheme = '%s\t' % v0_scheme + '\t'.join('%d' % x for x in [quotas.time_ms,
        quotas.sz_bytes, quotas.reset_interval_ms, quotas.weight_sz_permil,
        quotas.weight_nr_accesses_permil, quotas.weight_age_permil,
        watermarks.metric, watermarks.interval_us, watermarks.high_permil,
        watermarks.mid_permil, watermarks.low_permil])

    if scheme_version == 0:
        return v0_scheme
    elif scheme_version == 1:
        return v1_scheme
    elif scheme_version == 2:
        return v2_scheme
    elif scheme_version == 3:
        return v3_scheme
    elif scheme_version == 4:
        return v4_scheme
    else:
        print('Unsupported scheme version: %d' % scheme_version)
        exit(1)

def debugfs_scheme(line, sample_interval, aggr_interval, scheme_version):
    damos = damo_scheme_to_damos(line, scheme_version)
    return damos_to_debugfs_input(damos, sample_interval, aggr_interval,
            scheme_version)

def convert(schemes, sample_interval, aggr_interval, scheme_version):
    if os.path.isfile(schemes):
        with open(schemes, 'r') as f:
            schemes = f.read()

    raw_lines = schemes.split('\n')
    converted_lines = []
    for line in raw_lines:
        if line.startswith('#'):
            continue
        line = line.strip()
        if line == '':
            continue
        converted_lines.append(debugfs_scheme(line, sample_interval,
            aggr_interval, scheme_version))
    return '\n'.join(converted_lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', metavar='<file or schemes in text>',
            help='input file describing the schemes or the schemes')
    parser.add_argument('-s', '--sample', metavar='<interval>', type=int,
            default=5000, help='sampling interval (us)')
    parser.add_argument('-a', '--aggr', metavar='<interval>', type=int,
            default=100000, help='aggregation interval (us)')
    parser.add_argument('--scheme_version', metavar='<version>', type=int,
            choices=range(0, 5), default=4, help='destination scheme version')
    args = parser.parse_args()

    sample_interval = args.sample
    aggr_interval = args.aggr
    scheme_ver = args.scheme_version

    print(convert(args.input, sample_interval, aggr_interval, scheme_ver))

if __name__ == '__main__':
    main()
