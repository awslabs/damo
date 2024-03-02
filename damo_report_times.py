# SPDX-License-Identifier: GPL-2.0

import argparse
import subprocess

import _damon
import _damon_records
import damo_show

def main(args):
    access_pattern = _damon.DamosAccessPattern(args.sz_region,
            args.access_rate, _damon.unit_percent, args.age * 1000000,
            _damon.unit_usec)

    addr_range = None
    if args.address != None:
        addr_range, err = damo_show.parse_sort_addr_ranges_input(args.address)
        if err != None:
            print('wrong --address input (%s)' % err)
            exit(1)

    records, err = _damon_records.get_records(
                tried_regions_of=False, record_file=args.inputs[0],
                access_pattern=access_pattern, address_ranges=addr_range,
                total_sz_only=False, dont_merge_regions=False)
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

    for interval in times:
        print('-'.join(['%f' % (t / 1000000000) for t in interval]))

def set_argparser(parser):
    parser.add_argument('--inputs', metavar='<file>', nargs=2,
                        default=['damon.data', 'damon.data.profile'],
                        help='access pattern and profile record files')
    _damon_records.set_access_pattern_argparser(parser)

    parser.description='Show times of record having specific access pattern'
