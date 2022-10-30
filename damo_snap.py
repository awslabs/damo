#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Snap DAMON monitoring results.
"""

import argparse

import _damo_fmt_str
import _damon
import _damon_result

def set_argparser(parser):
    _damon.set_common_argparser(parser)
    parser.add_argument('--store_to', default='damon.snap.data',
            help='file to store the snapshot')
    parser.add_argument('--raw_number', action='store_true',
            help='use machine-friendly raw numbers')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    _damon.ensure_initialized(args, skip_dirs_population=True)

    if not _damon.feature_supported('schemes_tried_regions'):
        print('schemes_tried_regions not supported')
        exit(1)

    if _damon.damon_interface() == 'debugfs':
        print('snap does not support debugfs interface at the moment')
        exit(1)

    if not _damon.is_damon_running():
        print('DAMON is not turned on')
        exit(1)

    _damon.update_schemes_tried_regions(0)
    kdamonds = _damon.current_kdamonds()
    tried_regions = kdamonds[0].contexts[0].schemes[0].tried_regions
    aggr_interval_us = kdamonds[0].contexts[0].intervals.aggr
    wss = 0
    print('# snapshot in last %s' %
            _damo_fmt_str.format_time(aggr_interval_us * 1000, args.raw_number))
    print('# %10s %12s  %12s  %11s %5s' %
            ('start_addr', 'end_addr', 'length', 'nr_accesses', 'age'))
    for r in tried_regions:
        sz = r.end - r.start
        if r.nr_accesses > 0:
            wss += sz
        print('%012x-%012x (%12s) %11d %5d' % (r.start, r.end,
            _damo_fmt_str.format_sz(sz, args.raw_number), r.nr_accesses, r.age))
    print('wss: %s' % _damo_fmt_str.format_sz(wss, args.raw_number))

    damon_result = _damon_result.DAMONResult()
    damon_result.start_time = 0
    damon_result.end_time = aggr_interval_us
    damon_result.nr_snapshots = 1
    damon_result.target_snapshots[0] = [_damon_result.DAMONSnapshot(0, 100000000,
        0)]
    damon_result.target_snapshots[0][0].regions = tried_regions
    _damon_result.write_damon_result(damon_result, args.store_to, 'perf_script',
            int('600', 8))

if __name__ == '__main__':
    main()
