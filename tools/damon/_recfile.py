#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import struct

fmt_version = 0

def set_fmt_version(f):
    global fmt_version

    mark = f.read(16)
    if mark == b'damon_recfmt_ver':
        fmt_version = struct.unpack('i', f.read(4))[0]
    else:
        fmt_version = 0
        f.seek(0)
    return fmt_version

def target_id(f):
    if fmt_version == 1:
        return struct.unpack('i', f.read(4))[0]
    else:
        return struct.unpack('L', f.read(8))[0]

def parse_time(bindat):
    "bindat should be 16 bytes"
    sec = struct.unpack('l', bindat[0:8])[0]
    nsec = struct.unpack('l', bindat[8:16])[0]
    return sec * 1000000000 + nsec;
