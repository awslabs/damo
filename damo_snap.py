#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Snap DAMON monitoring results.
"""

import argparse

import _damon

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

    tried_regions = _damon.tried_regions_of(0, 0, 0)
    wss = 0
    for region in tried_regions:
        sz = region.end - region.start
        if region.nr_accesses > 0:
            wss += sz
        print('%d-%d (%d): nr_accesses %d, age %d' % (region.start, region.end,
            sz, region.nr_accesses, region.age))
    print('wss: %d' % wss)

if __name__ == '__main__':
    main()
