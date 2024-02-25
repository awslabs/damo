# SPDX-License-Identifier: GPL-2.0

import os
import random
import time

import _damo_fmt_str
import _damon_records
import damo_record_info

page_map = {}

def get_page(pfn):
    if not pfn in page_map:
        page_map[pfn] = bytearray(4096)
    return page_map[pfn]

def access_region(start_addr, end_addr):
    for addr in range(start_addr, end_addr, 4096):
        page = get_page(addr / 4096)
        not_real_use = 0
        for a in range(0, 4096, 4096):
            not_real_use += page[a]

def replay_snapshot(snapshot, mon_intervals):
    runtime_sec = (snapshot.end_time - snapshot.start_time) / 1000000000
    max_nr_accesses = mon_intervals.aggr / mon_intervals.sample
    time_slice = runtime_sec / max_nr_accesses
    nr_slices = int(runtime_sec / time_slice)
    for slice_idx in range(nr_slices):
        start_time = time.time()
        for region in snapshot.regions:
            if slice_idx < region.nr_accesses.samples:
                access_region(region.start, region.end)
        while time.time() - start_time < time_slice:
            pass

def test_perf(size_mem):
    access_start_time = time.time()
    next_output_time = time.time() + 1
    nr_accesses = 0
    while True:
        access_region(0, size_mem)
        nr_accesses += 1

        if time.time() >= next_output_time:
            print('replayer can access %s memory per second' %
                  _damo_fmt_str.format_sz(
                      size_mem * nr_accesses /
                      (time.time() - access_start_time),
                      machine_friendly=False))
            next_output_time = time.time() + 1
            nr_accesses = 0
            access_start_time = time.time()

def main(args):
    if args.test_perf is not None:
        size_mem = _damo_fmt_str.text_to_bytes(args.test_perf)
        return test_perf(size_mem)

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

    progress_notice_interval = args.progress_notice_interval
    if progress_notice_interval is None:
        progress_notice_interval = 3

    progress_notice_time = time.time() + progress_notice_interval
    for idx, snapshot in enumerate(record.snapshots):
        replay_snapshot(snapshot, record.intervals)
        if time.time() >= progress_notice_time:
            print('%d/%d snapshot replayed' % (idx, len(record.snapshots)))
            progress_notice_time += progress_notice_interval
    print('all snapshots are replayed')

def set_argparser(parser):
    parser.add_argument('--input', metavar='<file>', default='damon.data',
                        help='record file to replay')
    parser.add_argument('--progress_notice_interval', metavar='<seconds>',
                        type=float,
                        help='time interval between replay progress notice')
    parser.add_argument(
            '--test_perf', metavar='<bytes>',
            help='measure performance of replayer for given amount of memory')
    parser.description = 'Replay monitored access pattern'
    return parser
