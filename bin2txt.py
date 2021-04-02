#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import sys

import _read_record

def set_argparser(parser):
    parser.add_argument('--input', '-i', type=str, metavar='<file>',
            default='damon.data', help='input file name')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    file_path = args.input

    if not os.path.isfile(file_path):
        print('input file (%s) is not exist' % file_path)
        exit(1)

    record = _read_record.read_record(file_path)
    if not record:
        print('no record in the file')
    print('start_time: ', record.start_time)
    for snapshot in record.snapshots:
        print('rel time: %16d' % (snapshot.monitored_time - record.start_time))
        print('nr_tasks:  1')
        print('target_id: ', snapshot.target_id)
        print('nr_regions: ', len(snapshot.regions))
        for r in snapshot.regions:
            print("%012x-%012x(%10d):\t%d" %
                    (r.start, r.end, r.end - r.start, r.nr_accesses))
        print()

if __name__ == '__main__':
    main()
