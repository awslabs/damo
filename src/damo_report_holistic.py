# SPDX-License-Identifier: GPL-2.0

import argparse

import _damo_records
import damo_heatmap
import damo_record_info

def main(args):
    if args.footprints is None:
        args.footprints = args.access_pattern + '.mem_footprint'
    records, err = _damo_records.get_records(record_file=args.access_pattern)
    if err is not None:
        print('access pattern record file (%s) parsing failed (%s)' %
              (args.access_pattern, err))
        exit(1)

    guides = damo_record_info.get_guide_info(records)

    print('Overall recorded access pattern')
    print('===============================')
    print()
    for guide in guides:
        print(guide)
    print()
    print('# regions above are regions that access pattern recorded')
    print('# you can get this via \'damo record_info\', too')

    print()
    print('Heatmap')
    print('=======')
    print()
    for guide in guides:
        print('# target %d' % guide.tid)
        for region in guide.regions():
            print('# address range %d-%d' % (region[0], region[1]))
            damo_heatmap.pr_heats(
                    argparse.Namespace(
                        tid=guide.tid, resol=[20, 80],
                        time_range=[guide.start_time, guide.end_time],
                        address_range=region,
                        output='stdout',
                        stdout_colorset='gray',
                        stdout_skip_colorset_example=False,
                        ),
                    records)

def set_argparser(parser):
    parser.add_argument(
            '--access_pattern', metavar='<file>', default='damon.data',
            help='access pattern record file')
    parser.add_argument(
            '--footprints', metavar='<file>',
            help='memory footprints record file')
    parser.description = 'Show a holistic access pattern report'
