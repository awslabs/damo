#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import sys
import unittest

bindir = os.path.dirname(os.path.realpath(__file__))
damo_dir = os.path.join(bindir, '..', '..')
sys.path.append(damo_dir)

import _damon
import _damon_args
import _damon_sysfs

class TestDamonArgs(unittest.TestCase):
    def test_damon_ctx_from_args(self):
        _damon_sysfs.feature_supports = {'init_regions': True, 'schemes': True,
                'schemes_stat_qt_exceed': True, 'init_regions_target_idx':
                True, 'schemes_prioritization': True, 'schemes_tried_regions':
                False, 'record': False, 'schemes_quotas': True, 'fvaddr':
                False, 'paddr': True, 'schemes_wmarks': True,
                'schemes_speed_limit': True, 'schemes_stat_succ': True,
                'vaddr': True}
        _damon._damon_fs = _damon_sysfs

        parser = argparse.ArgumentParser()
        _damon_args.set_implicit_target_monitoring_argparser(parser)

        args = parser.parse_args(
                ('--sample 5000 --aggr 100000 --updr 1000000 ' +
                    '--minr 10 --maxr 1000 --regions=123-456 paddr').split())
        err = _damon_args.set_implicit_target_args_explicit(args)
        self.assertEqual(err, None)
        ctx, err = _damon_args.damon_ctx_from_args(args)
        self.assertEqual(err, None)
        self.assertEqual(ctx,
            _damon.DamonCtx('0',
                _damon.DamonIntervals(5000, 100000, 1000000),
                _damon.DamonNrRegionsRange(10, 1000), 'paddr',
                [_damon.DamonTarget('0', None,
                    [_damon.DamonRegion(123, 456)])],
                []))

        args = parser.parse_args(
                ('--sample 5ms --aggr 100ms --updr 1s ' +
                    '--minr 10 --maxr 1,000 --regions=1K-4K paddr').split())
        err = _damon_args.set_implicit_target_args_explicit(args)
        self.assertEqual(err, None)
        ctx, err = _damon_args.damon_ctx_from_args(args)
        self.assertEqual(err, None)
        self.assertEqual(ctx,
            _damon.DamonCtx('0',
                _damon.DamonIntervals(5000, 100000, 1000000),
                _damon.DamonNrRegionsRange(10, 1000), 'paddr',
                [_damon.DamonTarget('0', None,
                    [_damon.DamonRegion(1024, 4096)])],
                []))

        parser = argparse.ArgumentParser()
        _damon_args.set_explicit_target_argparser(parser)

        args = parser.parse_args(
                ('--sample 5ms --aggr 100ms --updr 1s ' +
                    '--minr 10 --maxr 1,000 --regions=1K-4K ' +
                    '--ops paddr').split())
        ctx, err = _damon_args.damon_ctx_from_args(args)
        self.assertEqual(err, None)
        self.assertEqual(ctx,
            _damon.DamonCtx('0',
                _damon.DamonIntervals(5000, 100000, 1000000),
                _damon.DamonNrRegionsRange(10, 1000), 'paddr',
                [_damon.DamonTarget('0', None,
                    [_damon.DamonRegion(1024, 4096)])],
                [_damon.Damos()]))

    def test_damon_intervals_from_args(self):
        parser = argparse.ArgumentParser()
        _damon_args.set_monitoring_attrs_argparser(parser)

        args = parser.parse_args(
                '--monitoring_intervals 4ms 120ms 1.5s'.split())
        intervals = _damon_args.damon_intervals_from_args(args)
        self.assertEqual(intervals, _damon.DamonIntervals('4ms', '120ms',
            '1.5s'))

        args = parser.parse_args('--sample 7ms'.split())
        intervals = _damon_args.damon_intervals_from_args(args)
        self.assertEqual(intervals, _damon.DamonIntervals('7ms'))

    def test_damon_nr_regions_range_from_args(self):
        parser = argparse.ArgumentParser()
        _damon_args.set_monitoring_attrs_argparser(parser)

        args = parser.parse_args(
                '--monitoring_nr_regions_range 25 5000'.split())
        nr_range = _damon_args.damon_nr_regions_range_from_args(args)
        self.assertEqual(nr_range, _damon.DamonNrRegionsRange(25, 5000))

if __name__ == '__main__':
    unittest.main()
