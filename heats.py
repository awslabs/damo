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

import _damon_result
import _fmt_nr

class HeatPixel:
    time = None
    addr = None
    heat = None

    def __init__(self, time, addr, heat):
        self.time = time
        self.addr = addr
        self.heat = heat

def add_heats(snapshot, duration, pixels, time_unit, space_unit, addr_range):
    """Add heats in a monitoring 'snapshot' of specific time 'duration' to
    the corresponding heats 'pixels'.
    """
    pixel_sz = time_unit * space_unit

    for region in snapshot.regions:
        start = max(region.start, addr_range[0])
        end = min(region.end, addr_range[1])
        if start >= end:
            continue

        fraction_start = start
        addr_idx = int(float(fraction_start - addr_range[0]) / space_unit)
        while fraction_start < end:
            fraction_end = min((addr_idx + 1) * space_unit + addr_range[0],
                    end)
            heat = region.nr_accesses * duration * (
                    fraction_end - fraction_start)

            pixel = pixels[addr_idx]
            heat += pixel.heat * pixel_sz
            pixel.heat = float(heat) / pixel_sz

            fraction_start = fraction_end
            addr_idx += 1

def heat_pixels_from_snapshots(snapshots, time_range, addr_range, resols):
    """Get heat pixels for monitoring snapshots."""
    time_unit = (time_range[1] - time_range[0]) / float(resols[0])
    space_unit = (addr_range[1] - addr_range[0]) / float(resols[1])

    pixels = [[HeatPixel(int(time_range[0] + i * time_unit),
                    int(addr_range[0] + j * space_unit), 0.0)
            for j in range(resols[1])] for i in range(resols[0])]

    if len(snapshots) < 2:
        return pixels

    for idx, shot in enumerate(snapshots[1:]):
        start = shot.start_time
        end = min(shot.end_time, time_range[1])

        fraction_start = start
        time_idx = int(float(fraction_start - time_range[0]) / time_unit)
        while fraction_start < end:
            fraction_end = min((time_idx + 1) * time_unit + time_range[0], end)
            add_heats(shot, fraction_end - fraction_start, pixels[time_idx],
                    time_unit, space_unit, addr_range)
            fraction_start = fraction_end
            time_idx += 1
    return pixels

def heatmap_plot_ascii(pixels, time_range, addr_range, resols, colorset):
    highest_heat = None
    lowest_heat = None
    for snapshot in pixels:
        for pixel in snapshot:
            if not highest_heat or highest_heat < pixel.heat:
                highest_heat = pixel.heat
            if not lowest_heat or lowest_heat > pixel.heat:
                lowest_heat = pixel.heat
    if not highest_heat and not lowest_heat:
        return
    heat_unit = float(highest_heat + 1 - lowest_heat) / 9

    colorsets = {
        'gray':[
            [232] * 10,
            [237, 239, 241, 243, 245, 247, 249, 251, 253, 255]],
        'flame':[
            [232, 1, 1, 2, 3, 3, 20, 21,26, 27, 27],
            [239, 235, 237, 239, 243, 245, 247, 249, 251, 255]],
        'emotion':[
            [232, 234, 20, 21, 26, 2, 3, 1, 1, 1],
            [239, 235, 237, 239, 243, 245, 247, 249, 251, 255]],
        }
    colors = colorsets[colorset]
    for snapshot in pixels:
        chars = []
        for pixel in snapshot:
            heat = int(float(pixel.heat - lowest_heat) / heat_unit)
            heat = min(heat, len(colors[0]) - 1)
            bg = colors[0][heat]
            fg = colors[1][heat]
            chars.append(u'\u001b[48;5;%dm\u001b[38;5;%dm%d' %
                    (bg, fg, heat))
        print(''.join(chars) + u'\u001b[0m')
    color_samples = [u'\u001b[48;5;%dm\u001b[38;5;%dm %d ' %
            (colors[0][i], colors[1][i], i) for i in range(10)]
    print('# access_frequency: %s' % ''.join(color_samples) + u'\u001b[0m')
    print('# x-axis: space (%d-%d: %s)' % (addr_range[0], addr_range[1],
        _fmt_nr.format_sz(addr_range[1] - addr_range[0], False)))
    print('# y-axis: time (%d-%d: %s)' % (time_range[0], time_range[1],
        _fmt_nr.format_time(time_range[1] - time_range[0], False)))
    print('# resolution: %dx%d (%s and %s for each character)' % (
        len(pixels[1]), len(pixels),
        _fmt_nr.format_sz(
            float(addr_range[1] - addr_range[0]) / len(pixels[1]), False),
        _fmt_nr.format_time(
            float(time_range[1] - time_range[0]) / len(pixels), False)))

def pr_heats(args, damon_result):
    tid = args.tid
    tres = args.resol[0]
    tmin = args.time_range[0]
    tmax = args.time_range[1]
    ares = args.resol[1]
    amin = args.address_range[0]
    amax = args.address_range[1]

    tunit = (tmax - tmin) // tres
    aunit = (amax - amin) // ares

    # Compensate the values so that those fit with the resolution
    tmax = tmin + tunit * tres
    amax = amin + aunit * ares

    # __pr_heats(damon_result, tid, tunit, tmin, tmax, aunit, amin, amax)

    snapshots = damon_result.target_snapshots[tid]
    pixels = heat_pixels_from_snapshots(snapshots, [tmin, tmax], [amin, amax],
            [tres, ares])

    if args.heatmap == 'stdout':
        heatmap_plot_ascii(pixels, [tmin, tmax], [amin, amax], [tres, ares],
                args.stdout_heatmap_color)
        return

    for row in pixels:
        for pixel in row:
            time = pixel.time
            addr = pixel.addr
            if not args.abs_time:
                time -= tmin
            if not args.abs_addr:
                addr -= amin

            print('%s\t%s\t%s' % (time, addr, pixel.heat))

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
        lines.append('time: %d-%d (%s)' % (self.start_time, self.end_time,
                    _fmt_nr.format_time(self.end_time - self.start_time,
                        False)))
        for idx, region in enumerate(self.regions()):
            lines.append('region\t%2d: %020d-%020d (%s)' %
                    (idx, region[0], region[1],
                        _fmt_nr.format_sz(region[1] - region[0], False)))
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
    for snapshots in damon_result.target_snapshots.values():
        for snapshot in snapshots:
            monitor_time = snapshot.end_time
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
    if args.tid and args.time_range and args.address_range:
        return
    guides = get_guide_info(damon_result)
    guide = guides[0]
    if not args.tid:
        args.tid = guide.tid
    for g in guides:
        if g.tid == args.tid:
            guide = g
            break

    if not args.time_range:
        args.time_range = [guide.start_time, guide.end_time]

    if not args.address_range:
        args.address_range = sorted(guide.regions(), key=lambda x: x[1] - x[0],
                reverse=True)[0]

def plot_range(orig_range, use_absolute_val):
    plot_range = [x for x in orig_range]
    if not use_absolute_val:
        plot_range[0] -= orig_range[0]
        plot_range[1] -= orig_range[0]
    return plot_range

def plot_heatmap(data_file, output_file, args):
    terminal = output_file.split('.')[-1]
    if not terminal in ['pdf', 'jpeg', 'png', 'svg']:
        os.remove(data_file)
        print("Unsupported plot output type.")
        exit(-1)

    x_range = plot_range(args.time_range, args.abs_time)
    y_range = plot_range(args.address_range, args.abs_addr)

    gnuplot_cmd = """
    set term %s;
    set output '%s';
    set key off;
    set xrange [%f:%f];
    set yrange [%f:%f];
    set xlabel 'Time (ns)';
    set ylabel 'Address (bytes)';
    plot '%s' using 1:2:3 with image;""" % (terminal, output_file, x_range[0],
            x_range[1], y_range[0], y_range[1], data_file)
    subprocess.call(['gnuplot', '-e', gnuplot_cmd])
    os.remove(data_file)

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')
    parser.add_argument('--input_type', choices=['record', 'perf_script'],
            default=None, help='input file\'s type')

    parser.add_argument('--tid', metavar='<id>', type=int,
            help='target id')
    parser.add_argument('--resol', metavar='<resolution>', type=int, nargs=2,
            default=[500, 500],
            help='resolutions for time and address axises')
    parser.add_argument('--time_range', metavar='<time>', type=int, nargs=2,
            help='start and end time of the output')
    parser.add_argument('--address_range', metavar='<address>', type=int,
            nargs=2, help='start and end address of the output')
    parser.add_argument('--abs_time', action='store_true', default=False,
            help='display absolute time in output')
    parser.add_argument('--abs_addr', action='store_true', default=False,
            help='display absolute address in output')

    parser.add_argument('--guide', action='store_true',
            help='print a guidance for the ranges and resolution settings')
    parser.add_argument('--heatmap', metavar='<file>', type=str,
            help='heatmap image file to create.  stdout for terminal output')
    parser.add_argument('--stdout_heatmap_color',
            choices=['gray', 'flame', 'emotion'], default='gray',
            help='color theme for access frequencies')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    damon_result = _damon_result.parse_damon_result(
            args.input, args.input_type)
    if not damon_result:
        print('monitoring result file (%s) parsing failed' % args.input)
        exit(1)

    # Use 80x40 resolution as default for ascii plot
    if args.heatmap == 'stdout' and args.resol == [500, 500]:
        args.resol = [40, 80]

    if args.guide:
        pr_guide(damon_result)
    else:
        set_missed_args(args, damon_result)
        orig_stdout = sys.stdout
        if args.heatmap and args.heatmap != 'stdout':
            tmp_path = tempfile.mkstemp()[1]
            tmp_file = open(tmp_path, 'w')
            sys.stdout = tmp_file

        pr_heats(args, damon_result)

        if args.heatmap and args.heatmap != 'stdout':
            sys.stdout = orig_stdout
            tmp_file.flush()
            tmp_file.close()
            plot_heatmap(tmp_path, args.heatmap, args)

if __name__ == '__main__':
    main()
