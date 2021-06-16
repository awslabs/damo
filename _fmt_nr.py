#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

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

