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
import _damon_dbgfs

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

    if not txt[-1] in unit_to_bytes:
        return int(txt)

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

    if not txt[-2:] in unit_to_usecs and not txt[-1] in unit_to_usecs:
        return float(txt)

    unit = txt[-2:]
    if unit in ['us', 'ms']:
        number = float(txt[:-2])
    else:
        unit = txt[-1]
        number = float(txt[:-1])
    return number * unit_to_usecs[unit]

def text_to_ms(txt):
    return int(text_to_us(txt) / 1000)

damos_action_to_int = {'willneed': 0, 'cold': 1, 'pageout': 2, 'hugepage': 3,
        'nohugepage': 4, 'stat': 5, 'lru_prio': 6, 'lru_deprio': 7}

def text_to_nr_accesses(txt, max_nr_accesses):
    if txt == 'min':
        return 0
    if txt == 'max':
        return max_nr_accesses

    return int(float(txt) * max_nr_accesses / 100)

def text_nr_accesses_percent(txt):
    if txt == 'min':
        return 0.0
    if txt == 'max':
        return 100.0
    return float(txt)

damos_wmark_metric_to_int = {'none': 0, 'free_mem_rate': 1}

def text_to_damos_wmark_metric(txt):
    return damos_wmark_metric_to_int[txt.lower()]

def damo_scheme_to_damos(line, name):
    '''Returns Damos object and err'''
    fields = line.split()
    expected_lengths = [7, 9, 12, 17, 18]
    if not len(fields) in expected_lengths:
        return None, 'expected %s fields, but \'%s\'' % (expected_lengths,
                line)

    try:
        min_sz = text_to_bytes(fields[0])
        max_sz = text_to_bytes(fields[1])
        min_nr_accesses = text_nr_accesses_percent(fields[2])
        max_nr_accesses = text_nr_accesses_percent(fields[3])
        nr_accesses_unit = 'percent'
        min_age = text_to_us(fields[4])
        max_age = text_to_us(fields[5])
        age_unit = 'usec'
        action_txt = fields[6].lower()
        quota_ms = 0
        quota_sz = 0
        window_ms = ulong_max
        weight_sz = 0
        weight_nr_accesses = 0
        weight_age = 0
        wmarks_txt = 'none'
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
                wmarks_txt = fields[12].lower()
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
            wmarks_txt = fields[13].lower()
            wmarks_metric = text_to_damos_wmark_metric(fields[13])
            wmarks_interval = text_to_us(fields[14])
            wmarks_high = int(fields[15])
            wmarks_mid = int(fields[16])
            wmarks_low = int(fields[17])

    except:
        return None, 'wrong input field'

    return _damon.Damos(name, _damon.DamosAccessPattern(min_sz, max_sz,
        min_nr_accesses, max_nr_accesses, nr_accesses_unit,
        min_age, max_age, age_unit),
        action_txt,
        _damon.DamosQuota(quota_ms, quota_sz, window_ms, weight_sz,
            weight_nr_accesses, weight_age),
        _damon.DamosWatermarks(wmarks_txt, wmarks_interval, wmarks_high,
            wmarks_mid, wmarks_low), None), None

def damo_schemes_split_remove_comments(schemes):
    raw_lines = schemes.split('\n')
    clean_lines = []
    for line in raw_lines:
        if line.startswith('#'):
            continue
        line = line.strip()
        if line == '':
            continue
        clean_lines.append(line)
    return clean_lines

def damo_schemes_to_damos(damo_schemes):
    if os.path.isfile(damo_schemes):
        with open(damo_schemes, 'r') as f:
            damo_schemes = f.read()

    damos_list = []
    for idx, line in enumerate(
            damo_schemes_split_remove_comments(damo_schemes)):
        damos, err = damo_scheme_to_damos(line, '%d' % idx)
        if err != None:
            print('given scheme is neither file nor proper scheme string (%s)'
                    % err)
            exit(1)
        damos_list.append(damos)
    return damos_list

def damo_schemes_to_debugfs_input(schemes, sample_interval, aggr_interval,
        scheme_version):
    lines = []
    for damos in damo_schemes_to_damos(schemes):
        lines.append(
                _damon_dbgfs.damos_to_debugfs_input(damos, sample_interval,
                    aggr_interval, scheme_version))
    return '\n'.join(lines)
