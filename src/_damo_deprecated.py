# SPDX-License-Identifier: GPL-2.0

'''
Keep code for deprecated features, which still need to help old users migrate,
e.g., 'translate_damos' and 'convert_record_format'.
'''

import json
import os
import subprocess
import sys

import _damo_deprecation_notice
import _damo_fmt_str
import _damon

'''
Python2 support
'''

if sys.version.startswith('2.'):
    _damo_deprecation_notice.deprecated(feature='Python2 support of damo',
            deadline='2023-Q2')

# For supporting python 2.6
try:
    subprocess.DEVNULL = subprocess.DEVNULL
except AttributeError:
    subprocess.DEVNULL = open(os.devnull, 'wb')

try:
    subprocess.check_output = subprocess.check_output
except AttributeError:
    def check_output(*popenargs, **kwargs):
        process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
        output, err = process.communicate()
        rc = process.poll()
        if rc:
            raise subprocess.CalledProcessError(rc, popenargs[0])
        return output

    subprocess.check_output = check_output

'''
DAMOS single-line scheme specification input.

Change human readable data access monitoring-based operation schemes input for
'damo' to a '_damon.Damos' object.
This format has inspired by DAMON debugfs 'schemes' file input/output.  It was
enough to be used for the initial version, but later extending it made it to
receive more than 15 fields, and became hard to understand and maintain.
Hence, replaced by more intuitive command line options and json format.

Below are examples of the single-line scheme input.

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
'''

def fields_to_v0_scheme(fields):
    scheme = _damon.Damos()
    scheme.access_pattern = _damon.DamosAccessPattern(
            sz_bytes = [_damo_fmt_str.text_to_bytes(fields[0]),
                _damo_fmt_str.text_to_bytes(fields[1])],
            nr_accesses = [_damo_fmt_str.text_to_percent(fields[2]),
                _damo_fmt_str.text_to_percent(fields[3])],
            nr_accesses_unit = _damon.unit_percent,
            age = [_damo_fmt_str.text_to_us(fields[4]),
                _damo_fmt_str.text_to_us(fields[5])],
            age_unit = _damon.unit_usec)
    scheme.action = fields[6].lower()
    return scheme

def fields_to_v1_scheme(fields):
    scheme = fields_to_v0_scheme(fields)
    scheme.quotas.sz_bytes = _damo_fmt_str.text_to_bytes(fields[7])
    scheme.quotas.reset_interval_ms = _damo_fmt_str.text_to_ms(
            fields[8])
    return scheme

def fields_to_v2_scheme(fields):
    scheme = fields_to_v1_scheme(fields)
    scheme.quotas.weight_sz_permil = int(fields[9])
    scheme.quotas.weight_nr_accesses_permil = int(fields[10])
    scheme.quotas.weight_age_permil = int(fields[11])
    return scheme

def fields_to_v3_scheme(fields):
    scheme = fields_to_v2_scheme(fields)
    scheme.watermarks.metric = fields[12].lower()
    scheme.watermarks.interval_us = _damo_fmt_str.text_to_us(
            fields[13])
    scheme.watermarks.high_permil = int(fields[14])
    scheme.watermarks.mid_permil = int(fields[15])
    scheme.watermarks.low_permil = int(fields[16])
    return scheme

def fields_to_v4_scheme(fields):
    scheme = fields_to_v0_scheme(fields)
    scheme.quotas.time_ms = _damo_fmt_str.text_to_ms(fields[7])
    scheme.quotas.sz_bytes = _damo_fmt_str.text_to_bytes(fields[8])
    scheme.quotas.reset_interval_ms = _damo_fmt_str.text_to_ms(
            fields[9])
    scheme.quotas.weight_sz_permil = int(fields[10])
    scheme.quotas.weight_nr_accesses_permil = int(fields[11])
    scheme.quotas.weight_age_permil = int(fields[12])
    scheme.watermarks.metric = fields[13].lower()
    scheme.watermarks.interval_us = _damo_fmt_str.text_to_us(
            fields[14])
    scheme.watermarks.high_permil = int(fields[15])
    scheme.watermarks.mid_permil = int(fields[16])
    scheme.watermarks.low_permil = int(fields[17])
    return scheme

avoid_crashing_single_line_scheme_for_testing = False
avoid_crashing_v1_v3_schemes_for_testing = False
def damo_single_line_scheme_to_damos(line):
    '''Returns Damos object and err'''

    _damo_deprecation_notice.deprecated(
            feature='single line scheme input',
            deadline='2023-Q2',
            do_exit=not avoid_crashing_single_line_scheme_for_testing,
            exit_code=1,
            additional_notice='Please use json format or --damo_* options')

    fields = line.split()

    # Remove below if someone depends on the v1-v3  DAMOS input is found.
    if len(fields) in [9, 12, 17]:
        _damo_deprecation_notice.deprecated(
                feature='9, 12, or 17 fields single line scheme input',
                do_exit=not avoid_crashing_v1_v3_schemes_for_testing,
                exit_code=1,
                deadline='2023-Q2')

    try:
        if len(fields) == 7:
            return fields_to_v0_scheme(fields), None
        elif len(fields) == 9:
            return fields_to_v1_scheme(fields), None
        elif len(fields) == 12:
            return fields_to_v2_scheme(fields), None
        elif len(fields) == 17:
            return fields_to_v3_scheme(fields), None
        elif len(fields) == 18:
            return fields_to_v4_scheme(fields), None
        else:
            return None, 'expected %s fields, but \'%s\'' % (
                    [7, 9, 12, 17, 18], line)
    except:
        return None, 'wrong input field'
    return None, 'unsupported version of single line scheme'

def damo_single_line_schemes_to_damos(schemes):
    if os.path.isfile(schemes):
        with open(schemes, 'r') as f:
            schemes = f.read()

    # remove comments, empty lines, and unnecessary white spaces
    damo_schemes_lines = [l.strip() for l in schemes.strip().split('\n')
            if not l.strip().startswith('#') and l.strip() != '']

    damos_list = []
    for line in damo_schemes_lines:
        damos, err = damo_single_line_scheme_to_damos(line)
        if err != None:
            return None, 'invalid input: %s' % err
        damos.name = '%d' % len(damos_list)
        damos_list.append(damos)
    return damos_list, None
