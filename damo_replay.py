# SPDX-License-Identifier: GPL-2.0

import os

import _damon_records
import damo_record_info

def replay_snapshot(snapshot):
    for region in snapshot.regions:
        print('access %s-%s with %s percent access rate for %s nanosecs' %
              (region.start, region.end, region.nr_accesses.percent,
               snapshot.end_time - snapshot.start_time))

def main(args):
    input_file = args.input

    if not os.path.isfile(input_file):
        print('input file (%s) not exists' % input_file)
        exit(1)

    records, err = _damon_records.get_records(record_file=input_file)
    if err:
        print('parsing damon records file (%s) failed (%s)' %
              (input_file, err))
        exit(1)

    if len(records) == 0:
        print('no monitoring records in the file')
        exit(1)

    if len(records) != 1:
        print('supporting only single record for now')

    record = records[0]
    for snapshot in record.snapshots:
        for region in snapshot.regions:
            region.nr_accesses.add_unset_unit(record.intervals)

    for snapshot in record.snapshots:
        replay_snapshot(snapshot)

def set_argparser(parser):
    parser.add_argument('--input', metavar='<file>', default='damon.data',
                        help='record file to replay')
    parser.description = 'Replay monitored access pattern'
    return parser
