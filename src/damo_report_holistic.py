# SPDX-License-Identifier: GPL-2.0

import _damo_records
import damo_record_info

def main(args):
    if args.footprints is None:
        args.footprints = args.access_pattern + '.mem_footprint'
    records, err = _damo_records.get_records(record_file=args.access_pattern)
    if err is not None:
        print('access pattern record file (%s) parsing failed (%s)' %
              (args.access_pattern, err))
        exit(1)

    print('Overall recorded access pattern')
    print('===============================')
    print()
    damo_record_info.pr_guide(records)
    print()
    print('# regions above are regions that access pattern recorded')
    print('# you can get this via \'damo record_info\', too')

def set_argparser(parser):
    parser.add_argument(
            '--access_pattern', metavar='<file>', default='damon.data',
            help='access pattern record file')
    parser.add_argument(
            '--footprints', metavar='<file>',
            help='memory footprints record file')
    parser.description = 'Show a holistic access pattern report'
