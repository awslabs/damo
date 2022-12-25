#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import platform

def format_nr(nr, machine_friendly):
    raw_string = '%d' % nr
    if machine_friendly:
        return raw_string
    fields = []
    for i in range(0, len(raw_string), 3):
        start_idx = max(0, len(raw_string) - i - 3)
        end_idx = len(raw_string) - i
        fields = [raw_string[start_idx:end_idx]] + fields
    return ','.join(fields)

def format_sz(sz_bytes, machine_friendly):
    if machine_friendly:
        return '%d' % sz_bytes

    sz_bytes = float(sz_bytes)
    if sz_bytes == float(ulong_max):
        return 'max'
    if sz_bytes > 1<<60:
        return '%.3f EiB' % (sz_bytes / (1<<60))
    if sz_bytes > 1<<50:
        return '%.3f PiB' % (sz_bytes / (1<<50))
    if sz_bytes > 1<<40:
        return '%.3f TiB' % (sz_bytes / (1<<40))
    if sz_bytes > 1<<30:
        return '%.3f GiB' % (sz_bytes / (1<<30))
    if sz_bytes > 1<<20:
        return '%.3f MiB' % (sz_bytes / (1<<20))
    if sz_bytes > 1<<10:
        return '%.3f KiB' % (sz_bytes / (1<<10))
    return '%d B' % sz_bytes

def format_addr_range(start, end, machine_friendly):
    return '[%s, %s) (%s)' % (
            format_nr(start, machine_friendly),
            format_nr(end, machine_friendly),
            format_sz(end - start, machine_friendly))

ns_ns = 1
us_ns = 1000
ms_ns = 1000 * us_ns
sec_ns = 1000 * ms_ns
minute_ns = 60 * sec_ns
hour_ns = 60 * minute_ns
day_ns = 24 * hour_ns

nsecs_to_unit = {1: 'ns', us_ns: 'us', ms_ns: 'ms', sec_ns: 's',
        minute_ns: 'm', hour_ns: 'h', day_ns: 'd'}

def format_time_ns_min_unit(time_ns, min_unit, machine_friendly):
    if machine_friendly:
        return '%d' % time_ns

    if time_ns >= ulong_max:
        return 'max'

    for unit_nsecs in sorted(nsecs_to_unit.keys(), reverse=True):
        if time_ns < unit_nsecs:
            continue
        if unit_nsecs == min_unit:
            if time_ns % unit_nsecs:
                return '%.3f %s' % (time_ns / unit_nsecs,
                        nsecs_to_unit[unit_nsecs])
            else:
                return '%d %s' % (time_ns / unit_nsecs,
                        nsecs_to_unit[unit_nsecs])

        unit_nr = int(time_ns / unit_nsecs)
        unit_str = '%s %s' % (
                format_nr(unit_nr, False), nsecs_to_unit[unit_nsecs])

        less_unit_ns = time_ns - unit_nr * unit_nsecs
        if less_unit_ns == 0:
            return unit_str
        else:
            return '%s %s' % (unit_str, format_time_ns_min_unit(less_unit_ns,
                min_unit, False))
    return '0 ns'

def format_time_ns_exact(time_ns, machine_friendly):
    return format_time_ns_min_unit(time_ns, ns_ns, machine_friendly)

def format_time_us_exact(time_us, machine_friendly):
    return format_time_ns_exact(time_us * us_ns, machine_friendly)

def format_time_ns(time_ns, machine_friendly):
    if machine_friendly:
        return '%d' % time_ns

    time_ns = float(time_ns)
    if time_ns >= hour_ns:
        hour = int(time_ns / hour_ns)
        hour_str = '%d h' % hour

        less_hour_ns = time_ns - (hour * hour_ns)
        if less_hour_ns == 0:
            return hour_str
        return '%s %s' % (hour_str, format_time_ns(less_hour_ns, False))
    if time_ns >= minute_ns:
        if time_ns % minute_ns == 0:
            return '%d m' % (time_ns / minute_ns)
        if time_ns % sec_ns == 0:
            return '%d m %d s' % (time_ns / minute_ns,
                    (time_ns % minute_ns) / sec_ns)
        return '%d m %.3f s' % (time_ns / minute_ns,
                (time_ns % minute_ns) / sec_ns)
    if time_ns >= sec_ns:
        if time_ns % sec_ns == 0:
            return '%d s' % (time_ns / sec_ns)
        return '%.3f s' % (time_ns / sec_ns)
    if time_ns >= ms_ns:
        if time_ns % ms_ns == 0:
            return '%d ms' % (time_ns / ms_ns)
        return '%.3f ms' % (time_ns / ms_ns)
    if time_ns >= us_ns:
        if time_ns % us_ns == 0:
            return '%d us' % (time_ns / us_ns)
        return '%.3f us' % (time_ns / us_ns)
    return '%d ns' % time_ns

def format_time_us(time_us, machine_friendly):
    if machine_friendly:
        return '%d' % time_us

    return format_time_ns(time_us * 1000, machine_friendly)

def format_time_ms(time_ms, machine_friendly):
    if machine_friendly:
        return '%d' % time_ms

    return format_time_ns(time_ms * 1000000, machine_friendly)

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

unit_to_bytes = {'B': 1, 'K': 1 << 10, 'KiB': 1 << 10,
        'M': 1 << 20, 'MiB': 1 << 20, 'G': 1 << 30, 'GiB': 1 << 30,
        'T': 1 << 40, 'TiB': 1 << 40, 'P': 1 << 50, 'PiB': 1 << 50,
        'E': 1 << 60, 'EiB': 1 << 60}

def text_to_bytes(txt):
    if type(txt) in number_types:
        return txt

    if txt == 'min':
        return 0
    if txt == 'max':
        return ulong_max

    unit = None
    if len(txt) > 3:
        unit = txt[len(txt) - 3:]
        if unit in unit_to_bytes:
            number = float(text_to_nr(txt[:-3]))
        else:
            unit = None

    if unit == None:
        if txt[-1] in unit_to_bytes:
            unit = txt[-1]
            number = float(text_to_nr(txt[:-1]))
        else:
            unit = 'B'
            number  = float(text_to_nr(txt))

    return min(ulong_max, int(number * unit_to_bytes[unit]))

unit_to_nsecs = {'ns': ns_ns, 'us': us_ns, 'ms': ms_ns, 's': sec_ns,
        'm': minute_ns, 'h': hour_ns, 'd': day_ns}

def text_to_ns(txt):
    if txt == 'min':
        return 0
    if txt == 'max':
        return ulong_max

    fields = txt.split()
    if len(fields) > 1:
        result_us = 0
        for i in range(0, len(fields), 2):
            result_us += text_to_ns(''.join(fields[i: i + 2]))
        return result_us

    if not txt[-2:] in unit_to_nsecs and not txt[-1] in unit_to_nsecs:
        return float(txt)

    unit = txt[-2:]
    if unit in ['ns', 'us', 'ms']:
        number = float(text_to_nr(txt[:-2]))
    else:
        unit = txt[-1]
        number = float(text_to_nr(txt[:-1]))
    return number * unit_to_nsecs[unit]

def text_to_us(txt):
    if type(txt) in number_types:
        return txt
    try:
        return float(txt)
    except:
        pass

    if txt == 'max':
        return ulong_max
    return text_to_ns(txt) / us_ns

def text_to_ms(txt):
    if type(txt) in number_types:
        return txt
    try:
        return float(txt)
    except:
        pass

    if txt == 'max':
        return ulong_max
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
    return float(text_to_nr(txt))

def text_to_nr(txt):
    if type(txt) in number_types:
        return txt

    new_txt = ''.join([c for c in txt if c != ','])
    return float(new_txt)

def text_to_nr_unit(txt):
    fields = txt.split()
    if len(fields) != 2:
        raise Exception('text_to_nr_unit requires two fields')
    return text_to_nr(fields[0]), fields[1]
