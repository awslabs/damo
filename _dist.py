#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import struct
import subprocess

class Region:
    start = None
    end = None
    nr_accesses = None

    def __init__(self, start, end, nr_accesses):
        self.start = start
        self.end = end
        self.nr_accesses = nr_accesses

def access_patterns(f):
    nr_regions = struct.unpack('I', f.read(4))[0]

    patterns = []
    for r in range(nr_regions):
        saddr = struct.unpack('L', f.read(8))[0]
        eaddr = struct.unpack('L', f.read(8))[0]
        nr_accesses = struct.unpack('I', f.read(4))[0]
        patterns.append(Region(saddr, eaddr, nr_accesses))
    return patterns

def plot_dist(data_file, output_file, xlabel, ylabel):
    terminal = output_file.split('.')[-1]
    if not terminal in ['pdf', 'jpeg', 'png', 'svg']:
        os.remove(data_file)
        print("Unsupported plot output type.")
        exit(-1)

    gnuplot_cmd = """
    set term %s;
    set output '%s';
    set key off;
    set xlabel '%s';
    set ylabel '%s';
    plot '%s' with linespoints;""" % (terminal, output_file, xlabel, ylabel,
            data_file)
    subprocess.call(['gnuplot', '-e', gnuplot_cmd])
    os.remove(data_file)
