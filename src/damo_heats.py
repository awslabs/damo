# SPDX-License-Identifier: GPL-2.0

"""
Transform DAMON monitoring results record into a heatmap.  The heatmap is
constructed with pixels that each shows when (time), which memory region
(space) was how frequently accessed (heat).  The time and space are represented
by the location of the pixel on the map, while the heat is represented by it's
color.

By default, the output shows the relative time, space, and heat values of each
pixel of the map on each line, like below.

    <time> <space> <heat>
    ...

By constructing the pixels based on the values, the user can draw more
human-readable heatmap.  gnuplot like plot tools can be used.  If '--heatmap'
option is given, this tool does that on behalf of the human when '--heatmap'
option is given.
"""

import damo_heatmap

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')

    parser.add_argument('--tid', metavar='<id>', type=int,
            help='target id')
    parser.add_argument('--resol', metavar='<resolution>', type=int, nargs=2,
            default=[500, 500],
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
    parser.add_argument('--heatmap', metavar='<file>', type=str,
            help='heatmap image file to create.  stdout for terminal output')
    parser.add_argument('--stdout_heatmap_color',
            choices=['gray', 'flame', 'emotion'],
            help='color theme for access frequencies')
    parser.add_argument('--ascii_color',
            choices=['gray', 'flame', 'emotion'],
            help='another name of stdout_heatmap_color')
    parser.add_argument('--plot_ascii', action='store_true',
            help='shortcut of \'--heatmap stdout\'')
    parser.add_argument('--stdout_heatmap_skip_color_example',
            action='store_true',
            help='skip printing example colors at the output')
    parser.description = 'Show when which address ranges were how frequently accessed'

def main(args=None):
    # --plot_ascii and --ascii_color is used in the demo screenshop[1].
    # Support those.
    #
    # [1] https://sjp38.github.io/img/masim_stairs_heatmap_ascii.png
    if args.heatmap == None and args.plot_ascii:
        args.heatmap = 'stdout'
    if args.ascii_color != None and args.stdout_heatmap_color == None:
        args.stdout_heatmap_color = args.ascii_color
    if args.ascii_color == None and args.stdout_heatmap_color == None:
        args.stdout_heatmap_color = 'gray'

    # convert arguments for damo heatmap
    if args.heatmap is None:
        args.output = 'raw'
    else:
        args.output = args.heatmap
        args.stdout_colorset = args.stdout_heatmap_color

    damo_heatmap.main(args)
