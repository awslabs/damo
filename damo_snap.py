#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Snap DAMON monitoring results.
"""

import argparse

import _damon

def pr_schemes_tried_regions(tried_regions_content):
    nr_tried_regions = len(tried_regions_content)
    wss = 0
    for r in range(nr_tried_regions):
        region = tried_regions_content['%d' % r]
        start, end, nr_accesses, age = [int(x) for x in [
            region['start'], region['end'],
            region['nr_accesses'], region['age']]]
        sz = end - start
        if nr_accesses > 0:
            wss += sz
        print('%d-%d (%d): nr_accesses %d, age %d' % (start, end, sz, 
            nr_accesses, age))
    print('wss: %d' % wss)

def set_argparser(parser):
    _damon.set_common_argparser(parser)

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

    _damon.write_damon_fs({'kdamonds/0/state': 'update_schemes_tried_regions'})
    pr_schemes_tried_regions(_damon.read_damon_fs_from(
        'kdamonds/0/contexts/0/schemes/0/tried_regions/'))

if __name__ == '__main__':
    main()
