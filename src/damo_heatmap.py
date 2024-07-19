# SPDX-License-Identifier: GPL-2.0

"""
Transform DAMON monitoring results record into a heatmap.  The heatmap is
constructed with pixels that each shows when (time), which memory region
(space) was how frequently accessed (heat).  The time and space are represented
by the location of the pixel on the map, while the heat is represented by it's
color.

By default, the output shows the heatmap on the terminal.

If --output raw is given, the output shows the relative time, space, and heat
values of each pixel of the map on each line, like below.

    <time> <space> <heat>
    ...

By constructing the pixels based on the values, the user can draw more
human-readable heatmap.  gnuplot like plot tools can be used.  If '--heatmap'
option is given, this tool does that on behalf of the human when '--heatmap'
option is given.

If --output option is given with a file, the gnuplot-based heatmap image is
generated as the file.
"""

import os
import subprocess
import sys
import tempfile

import _damo_ascii_color
import _damo_fmt_str
import _damo_records
import damo_record_info

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

    Args:
      snapshot:     Data access monitoring results for a specific time
                    (DamonSnapshot class).
      duration:     The time of the snapshot to count and add heats to the
                    pixels.
      pixels:       The heatmap pixels that the heats of the snapshot of the
                    duration will be added.
      time_unit:    Time length that represented by each pixel
      space_unit:   Memory address range size that represented by each pixel
      addr_range:   The entire address range of the heatmap
    """
    pixel_sz = time_unit * space_unit

    for region in snapshot.regions:
        start = max(region.start, addr_range[0])
        end = min(region.end, addr_range[1])
        if start >= end:
            continue

        # The region and the corresponding pixel may not fit on the address
        # space.  Get a fraction of the region that overlaps with the pixel,
        # total heat (average heat * size of the fraction) of the fraction, and
        # add it to the corresponding pixel in size-average heat.
        fraction_start = start
        addr_idx = int(float(fraction_start - addr_range[0]) / space_unit)
        while fraction_start < end:
            fraction_end = min((addr_idx + 1) * space_unit + addr_range[0],
                    end)
            heat = region.nr_accesses.samples * duration * (
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

        # The snapshot's recorded time and the corresponding pixels row may not
        # fit on the time space.  Get a fraction of the time that both
        # overlaps, and add heats of the fractions to corresponding pixels.
        fraction_start = start
        time_idx = int(float(fraction_start - time_range[0]) / time_unit)
        while fraction_start < end:
            fraction_end = min((time_idx + 1) * time_unit + time_range[0], end)
            add_heats(shot, fraction_end - fraction_start, pixels[time_idx],
                    time_unit, space_unit, addr_range)
            fraction_start = fraction_end
            time_idx += 1
    return pixels

def fmt_ascii_heatmap(pixels, time_range, addr_range, resols, colorset,
        print_colorset):
    lines = []
    highest_heat = None
    lowest_heat = None
    for snapshot in pixels:
        for pixel in snapshot:
            if highest_heat == None or highest_heat < pixel.heat:
                highest_heat = pixel.heat
            if lowest_heat == None or lowest_heat > pixel.heat:
                lowest_heat = pixel.heat
    if highest_heat == None and lowest_heat == None:
        return
    heat_unit = float(highest_heat + 1 - lowest_heat) / 9

    for snapshot in pixels:
        chars = []
        for pixel in snapshot:
            heat = int(float(pixel.heat - lowest_heat) / heat_unit)
            heat = min(heat, _damo_ascii_color.max_color_level())
            chars.append('%s%d' %
                    (_damo_ascii_color.color_mode_start_txt(colorset, heat),
                        heat))
        lines.append(''.join(chars) + _damo_ascii_color.color_mode_end_txt())
    if print_colorset:
        lines.append('# access_frequency: %s' %
                _damo_ascii_color.color_samples(colorset))
    lines.append('# x-axis: space (%d-%d: %s)' % (addr_range[0], addr_range[1],
        _damo_fmt_str.format_sz(addr_range[1] - addr_range[0], False)))
    lines.append('# y-axis: time (%d-%d: %s)' % (time_range[0], time_range[1],
        _damo_fmt_str.format_time_ns(time_range[1] - time_range[0], False)))
    lines.append('# resolution: %dx%d (%s and %s for each character)' % (
        len(pixels[1]), len(pixels),
        _damo_fmt_str.format_sz(
            float(addr_range[1] - addr_range[0]) / len(pixels[1]), False),
        _damo_fmt_str.format_time_ns(
            float(time_range[1] - time_range[0]) / len(pixels), False)))
    return '\n'.join(lines)

def fmt_heats(args, __records):
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

    records = []
    for record in __records:
        if record.target_id == tid:
            records.append(record)

    lines = []
    for record in records:
        pixels = heat_pixels_from_snapshots(record.snapshots,
                [tmin, tmax], [amin, amax], [tres, ares])

        if args.output == 'stdout':
            lines.append(fmt_ascii_heatmap(pixels, [tmin, tmax], [amin, amax],
                    [tres, ares], args.stdout_colorset, not
                    args.stdout_skip_colorset_example))
            continue

        for row in pixels:
            for pixel in row:
                time = pixel.time
                addr = pixel.addr
                if not args.abs_time:
                    time -= tmin
                if not args.abs_addr:
                    addr -= amin

                lines.append('%s\t%s\t%s' % (time, addr, pixel.heat))
    return '\n'.join(lines)

def pr_heats(args, __records):
    print(fmt_heats(args, __records))

def set_missed_args(args, records):
    if args.tid and args.time_range and args.address_range:
        return
    guides = damo_record_info.get_guide_info(records)
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
        hottest_contig_region = sorted(
                guide.contig_regions, key=lambda x: x.heat_per_byte(),
                reverse=True)[0]
        args.address_range = [hottest_contig_region.start_addr,
                              hottest_contig_region.end_addr]

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
    try:
        subprocess.call(['gnuplot', '-e', gnuplot_cmd])
    except Exception as e:
        print('executing gnuplot failed (%s)' % e)
    os.remove(data_file)

def set_argparser(parser):
    parser.add_argument('--output', metavar='<output>', default='stdout',
                        help=' '.join(
                            ['output heatmap to generate.',
                             'can be a pdf/png/jpeg/svg file or',
                             'special keywords (\'stdout\', \'raw\')']))
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')

    parser.add_argument('--tid', metavar='<id>', type=int,
            help='target id')
    parser.add_argument('--resol', metavar='<resolution>', type=int, nargs=2,
            help='resolutions for time and address axes')
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
    parser.add_argument('--stdout_colorset', default='gray',
            choices=['gray', 'flame', 'emotion'],
            help='color theme for access frequencies')
    parser.add_argument('--stdout_skip_colorset_example',
            action='store_true',
            help='skip printing example colors at the output')
    parser.description = 'Show when which address ranges were how frequently accessed'

def main(args=None):
    records, err = _damo_records.get_records(record_file=args.input)
    if err != None:
        print('monitoring result file (%s) parsing failed (%s)' %
                (args.input, err))
        exit(1)

    # Use 80x40 or 500x500 resolution as default for stdout or image plots
    if args.resol is None:
        if args.output == 'stdout':
            args.resol = [40, 80]
        else:
            args.resol = [500, 500]

    if args.guide:
        damo_record_info.pr_guide(records)
        return

    set_missed_args(args, records)
    if args.output in ['stdout', 'raw']:
        pr_heats(args, records)
        return

    # use gnuplot-based image plot
    tmp_path = tempfile.mkstemp()[1]
    with open(tmp_path, 'w') as f:
        f.write(fmt_heats(args, records))
    plot_heatmap(tmp_path, args.output, args)
