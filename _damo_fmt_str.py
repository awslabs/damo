#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import platform

def format_sz(sz_bytes, machine_friendly):
    if machine_friendly:
        return '%d' % sz_bytes

    sz_bytes = float(sz_bytes)
    if sz_bytes > 1<<40:
        return '%.3f TiB' % (sz_bytes / (1<<40))
    if sz_bytes > 1<<30:
        return '%.3f GiB' % (sz_bytes / (1<<30))
    if sz_bytes > 1<<20:
        return '%.3f MiB' % (sz_bytes / (1<<20))
    if sz_bytes > 1<<10:
        return '%.3f KiB' % (sz_bytes / (1<<10))
    return '%d B' % sz_bytes

def format_time(time_ns, machine_friendly):
    if machine_friendly:
        return '%d' % time_ns

    time_ns = float(time_ns)
    if time_ns > 60000000000:
        return '%d m %.3f s' % (time_ns / 60000000000,
                (time_ns % 60000000000) / 1000000000)
    if time_ns > 1000000000:
        return '%.3f s' % (time_ns / 1000000000)
    if time_ns > 1000000:
        return '%.3f ms' % (time_ns / 1000000)
    if time_ns > 1000:
        return '%.3f us' % (time_ns / 1000)
    return '%d ns' % time_ns

def indent_lines(string, indent_width):
    return '\n'.join([' ' * indent_width + l for l in string.split('\n')])

number_types = [int, float]

try:
    # for python2
    number_types.append(long)
except:
    pass

uint_max = 2**32 - 1
ulong_max = 2**64 - 1
if platform.architecture()[0] != '64bit':
    ulong_max = 2**32 - 1

unit_to_bytes = {'B': 1, 'K': 1024, 'M': 1024 * 1024, 'G': 1024 * 1024 * 1024,
        'T': 1024 * 1024 * 1024 * 1024}

def text_to_bytes(txt):
    if type(txt) in number_types:
        return txt

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
    if type(txt) in number_types:
        return txt

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
    if type(txt) in number_types:
        return txt

    return int(text_to_us(txt) / 1000)

def text_to_percent(txt):
    if type(txt) in number_types:
        return txt

    if txt == 'min':
        return 0.0
    if txt == 'max':
        return 100.0
    if txt[-1] == '%':
        txt = txt[:-1]
    return float(txt)
