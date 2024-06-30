# SPDX-License-Identifier: GPL-2.0

import argparse

import _damo_dist
import _damo_fmt_str
import _damo_records
import damo_heatmap
import damo_record_info
import damo_report_footprint
import damo_wss

def main(args):
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
    print('# you can get above via \'damo report heatmap\'')

    print()
    print('Working Set Size Distribution')
    print('=============================')
    print()
    _damo_records.adjust_records(
            records, aggregate_interval=1, nr_snapshots_to_skip=20)
    for sort_key in ['size', 'time']:
        print('Sorted by %s' % sort_key)
        print('--------------')
        print()
        wss_dists = damo_wss.get_wss_dists(
                records, acc_thres=1, sz_thres=1, do_sort=sort_key,
                collapse_targets=True)
        for tid, dists in wss_dists.items():
            # because collapsed targets, only one iteration will be executed here
            _damo_dist.pr_dists(
                    'wss', dists, range(0, 101, 25), pr_all=False,
                    format_fn=_damo_fmt_str.format_sz, raw_number=False,
                    nr_cols_bar=59)
        print()
    print('# you can get above via \'damo report wss\'')

    print()
    print('Memory Footprints Distribution')
    print('==============================')
    print()

    if args.footprints is None:
        args.footprints = args.access_pattern + '.mem_footprint'

    for sort_key in ['size', 'time']:
        print('Sorted by %s' % sort_key)
        print('--------------')
        print()
        damo_report_footprint.main(
                argparse.Namespace(
                    metric='all', input=args.footprints, range=[0, 101, 25],
                    sortby=sort_key, plot=None, nr_cols_bar=59, raw_number=False,
                    all_footprint=False))
        print()
    print('# you can get above via \'damo report footprints\'')

def set_argparser(parser):
    parser.add_argument(
            '--access_pattern', metavar='<file>', default='damon.data',
            help='access pattern record file')
    parser.add_argument(
            '--footprints', metavar='<file>',
            help='memory footprints record file')
    parser.description = 'Show a holistic access pattern report'
