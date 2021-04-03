#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Transform binary trace data into human readable text that can be used for
heatmap drawing, or directly plot the data in a heatmap format.

Format of the text is:

    <time> <space> <heat>
    ...

"""

import argparse
import os
import subprocess
import sys
import tempfile

import _parse_damon_result

class HeatSample:
    space_idx = None
    sz_time_space = None
    heat = None

    def __init__(self, space_idx, sz_time_space, heat):
        if sz_time_space < 0:
            raise RuntimeError()
        self.space_idx = space_idx
        self.sz_time_space = sz_time_space
        self.heat = heat

    def total_heat(self):
        return self.heat * self.sz_time_space

    def merge(self, sample):
        "sample must have a space idx that same to self"
        heat_sum = self.total_heat() + sample.total_heat()
        self.heat = heat_sum / (self.sz_time_space + sample.sz_time_space)
        self.sz_time_space += sample.sz_time_space

def pr_samples(samples, time_idx, time_unit, region_unit):
    display_time = time_idx * time_unit
    for idx, sample in enumerate(samples):
        display_addr = idx * region_unit
        if not sample:
            print("%s\t%s\t%s" % (display_time, display_addr, 0.0))
            continue
        print("%s\t%s\t%s" % (display_time, display_addr, sample.total_heat() /
            time_unit / region_unit))

def to_idx(value, min_, unit):
    return (value - min_) // unit

def read_task_heats(snapshot, aunit, amin, amax):
    tid_ = snapshot.target_id
    samples = []
    for r in snapshot.regions:
        saddr = r.start
        eaddr = min(r.end, amax - 1)
        heat = r.nr_accesses

        if eaddr <= amin:
            continue
        if saddr >= amax:
            continue
        saddr = max(amin, saddr)
        eaddr = min(amax, eaddr)

        sidx = to_idx(saddr, amin, aunit)
        eidx = to_idx(eaddr - 1, amin, aunit)
        for idx in range(sidx, eidx + 1):
            sa = max(amin + idx * aunit, saddr)
            ea = min(amin + (idx + 1) * aunit, eaddr)
            sample = HeatSample(idx, (ea - sa), heat)
            samples.append(sample)
    return samples

def apply_samples(target_samples, samples, start_time, end_time, aunit, amin):
    for s in samples:
        sample = HeatSample(s.space_idx,
                s.sz_time_space * (end_time - start_time), s.heat)
        idx = sample.space_idx
        if not target_samples[idx]:
            target_samples[idx] = sample
        else:
            target_samples[idx].merge(sample)

def __pr_heats(damon_result, tid, tunit, tmin, tmax, aunit, amin, amax):
    heat_samples = [None] * ((amax - amin) // aunit)

    start_time = 0
    end_time = 0
    last_flushed = -1

    for snapshot in damon_result.snapshots:
        if snapshot.target_id != tid:
            continue
        start_time = end_time
        end_time = snapshot.monitored_time
        samples_set = {}
        samples = read_task_heats(snapshot, aunit, amin, amax)
        if samples:
            samples_set[tid] = samples
        if not tid in samples_set:
            continue
        if start_time >= tmax:
            continue
        if end_time <= tmin:
            continue
        start_time = max(start_time, tmin)
        end_time = min(end_time, tmax)

        sidx = to_idx(start_time, tmin, tunit)
        eidx = to_idx(end_time - 1, tmin, tunit)
        for idx in range(sidx, eidx + 1):
            if idx != last_flushed:
                pr_samples(heat_samples, idx, tunit, aunit)
                heat_samples = [None] * ((amax - amin) // aunit)
                last_flushed = idx
            st = max(start_time, tmin + idx * tunit)
            et = min(end_time, tmin + (idx + 1) * tunit)
            apply_samples(heat_samples, samples_set[tid], st, et, aunit, amin)

def pr_heats(args, damon_result):
    tid = args.tid
    tres = args.tres
    tmin = args.tmin
    ares = args.ares
    amin = args.amin

    tunit = (args.tmax - tmin) // tres
    aunit = (args.amax - amin) // ares

    # Compensate the values so that those fit with the resolution
    tmax = tmin + tunit * tres
    amax = amin + aunit * ares

    __pr_heats(damon_result, tid, tunit, tmin, tmax, aunit, amin, amax)

class GuideInfo:
    tid = None
    start_time = None
    end_time = None
    lowest_addr = None
    highest_addr = None
    gaps = None

    def __init__(self, tid, start_time):
        self.tid = tid
        self.start_time = start_time
        self.gaps = []

    def regions(self):
        regions = []
        region = [self.lowest_addr]
        for gap in self.gaps:
            for idx, point in enumerate(gap):
                if idx == 0:
                    region.append(point)
                    regions.append(region)
                else:
                    region = [point]
        region.append(self.highest_addr)
        regions.append(region)
        return regions

    def total_space(self):
        ret = 0
        for r in self.regions():
            ret += r[1] - r[0]
        return ret

    def __str__(self):
        lines = ['target_id:%d' % self.tid]
        lines.append('time: %d-%d (%d)' % (self.start_time, self.end_time,
                    self.end_time - self.start_time))
        for idx, region in enumerate(self.regions()):
            lines.append('region\t%2d: %020d-%020d (%d)' %
                    (idx, region[0], region[1], region[1] - region[0]))
        return '\n'.join(lines)

def is_overlap(region1, region2):
    if region1[1] < region2[0]:
        return False
    if region2[1] < region1[0]:
        return False
    return True

def overlap_region_of(region1, region2):
    return [max(region1[0], region2[0]), min(region1[1], region2[1])]

def overlapping_regions(regions1, regions2):
    overlap_regions = []
    for r1 in regions1:
        for r2 in regions2:
            if is_overlap(r1, r2):
                r1 = overlap_region_of(r1, r2)
        if r1:
            overlap_regions.append(r1)
    return overlap_regions

def get_guide_info(damon_result):
    "return the set of guide information for the moitoring result"
    guides = {}
    for snapshot in damon_result.snapshots:
        monitor_time = snapshot.monitored_time
        tid = snapshot.target_id
        if not tid in guides:
            guides[tid] = GuideInfo(tid, monitor_time)
        guide = guides[tid]
        guide.end_time = monitor_time

        last_addr = None
        gaps = []
        for r in snapshot.regions:
            saddr = r.start
            eaddr = r.end

            if not guide.lowest_addr or saddr < guide.lowest_addr:
                guide.lowest_addr = saddr
            if not guide.highest_addr or eaddr > guide.highest_addr:
                guide.highest_addr = eaddr

            if not last_addr:
                last_addr = eaddr
                continue
            if last_addr != saddr:
                gaps.append([last_addr, saddr])
            last_addr = eaddr

        if not guide.gaps:
            guide.gaps = gaps
        else:
            guide.gaps = overlapping_regions(guide.gaps, gaps)

    return sorted(list(guides.values()), key=lambda x: x.total_space(),
                    reverse=True)

def pr_guide(damon_result):
    for guide in get_guide_info(damon_result):
        print(guide)

def region_sort_key(region):
    return region[1] - region[0]

def set_missed_args(args, damon_result):
    if args.tid and args.tmin and args.tmax and args.amin and args.amax:
        return
    guides = get_guide_info(damon_result)
    guide = guides[0]
    if not args.tid:
        args.tid = guide.tid
    for g in guides:
        if g.tid == args.tid:
            guide = g
            break

    if not args.tmin:
        args.tmin = guide.start_time
    if not args.tmax:
        args.tmax = guide.end_time

    if not args.amin or not args.amax:
        region = sorted(guide.regions(), key=lambda x: x[1] - x[0],
                reverse=True)[0]
        args.amin = region[0]
        args.amax = region[1]

def plot_heatmap(data_file, output_file):
    terminal = output_file.split('.')[-1]
    if not terminal in ['pdf', 'jpeg', 'png', 'svg']:
        os.remove(data_file)
        print("Unsupported plot output type.")
        exit(-1)

    gnuplot_cmd = """
    set term %s;
    set output '%s';
    set key off;
    set xrange [0:];
    set yrange [0:];
    set xlabel 'Time (ns)';
    set ylabel 'Address (bytes)';
    plot '%s' using 1:2:3 with image;""" % (terminal, output_file, data_file)
    subprocess.call(['gnuplot', '-e', gnuplot_cmd])
    os.remove(data_file)

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--input_type', choices=['record', 'perf_script'],
            default='record', help='input file\'s type')
    parser.add_argument('--tid', metavar='<id>', type=int,
            help='target id')
    parser.add_argument('--tres', metavar='<resolution>', type=int,
            default=500, help='time resolution of the output')
    parser.add_argument('--tmin', metavar='<time>', type=lambda x: int(x,0),
            help='minimal time of the output')
    parser.add_argument('--tmax', metavar='<time>', type=lambda x: int(x,0),
            help='maximum time of the output')
    parser.add_argument('--ares', metavar='<resolution>', type=int, default=500,
            help='space address resolution of the output')
    parser.add_argument('--amin', metavar='<address>', type=lambda x: int(x,0),
            help='minimal space address of the output')
    parser.add_argument('--amax', metavar='<address>', type=lambda x: int(x,0),
            help='maximum space address of the output')
    parser.add_argument('--guide', action='store_true',
            help='print a guidance for the min/max/resolution settings')
    parser.add_argument('--heatmap', metavar='<file>', type=str,
            help='heatmap image file to create')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    if args.input_type == 'record':
        damon_result = _parse_damon_result.record_to_damon_result(args.input)
    elif args.input_type == 'perf_script':
        damon_result = _parse_damon_result.perf_script_to_damon_result(
                args.input)
    else:
        print('unknown input type')
        exit(1)

    if args.guide:
        pr_guide(damon_result)
    else:
        set_missed_args(args, damon_result)
        orig_stdout = sys.stdout
        if args.heatmap:
            tmp_path = tempfile.mkstemp()[1]
            tmp_file = open(tmp_path, 'w')
            sys.stdout = tmp_file

        pr_heats(args, damon_result)

        if args.heatmap:
            sys.stdout = orig_stdout
            tmp_file.flush()
            tmp_file.close()
            plot_heatmap(tmp_path, args.heatmap)

if __name__ == '__main__':
    main()
