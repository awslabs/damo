# SPDX-License-Identifier: GPL-2.0

import argparse
import subprocess

import _damon
import _damo_records
import damo_show

def main(args):
    record_filter, err = _damo_records.args_to_filter(args)
    if err != None:
        print(err)
        exit(1)

    records, err = _damo_records.get_records(
                tried_regions_of=False, record_file=args.inputs[0],
                record_filter=record_filter, total_sz_only=False,
                dont_merge_regions=False)
    if err != None:
        print(err)
        exit(1)

    times = []
    for record in records:
        for snapshot in record.snapshots:
            if len(snapshot.regions) == 0:
                continue
            if len(times) == 0:
                times.append([snapshot.start_time, snapshot.end_time])
                continue
            last_time = times[-1]
            if last_time[1] == snapshot.start_time:
                last_time[1] = snapshot.end_time
            else:
                times.append([snapshot.start_time, snapshot.end_time])

    if len(times) == 0:
        print('No snapshot of the condition found')
        exit(1)

    cmd = ['perf', 'report', '-i', args.inputs[1]]
    for interval in times:
        cmd += ['--time', ','.join(['%s' % (t / 1000000000) for t in interval])]
    subprocess.call(cmd)

def set_argparser(parser):
    parser.add_argument('--inputs', metavar='<file>', nargs=2,
                        default=['damon.data', 'damon.data.profile'],
                        help='access pattern and profile record files')
    _damo_records.set_filter_argparser(parser)

    parser.description='Show profiling report for specific access pattern'
