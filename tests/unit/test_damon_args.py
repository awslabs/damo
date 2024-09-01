#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damon
import _damon_args
import _damon_sysfs

class TestDamonArgs(unittest.TestCase):
    def test_damon_ctx_for(self):
        _damon._damon_fs = _damon_sysfs
        _damon.set_feature_supports({'init_regions': True, 'schemes': True,
                'schemes_stat_qt_exceed': True, 'init_regions_target_idx':
                True, 'schemes_prioritization': True, 'schemes_tried_regions':
                False, 'record': False, 'schemes_quotas': True, 'fvaddr':
                False, 'paddr': True, 'schemes_wmarks': True,
                'schemes_speed_limit': True, 'schemes_stat_succ': True,
                'vaddr': True})

        parser = argparse.ArgumentParser()
        _damon_args.set_argparser(
                parser, add_record_options=False, min_help=True)

        args = parser.parse_args(
                ('--sample 5000 --aggr 100000 --updr 1000000 ' +
                    '--minr 10 --maxr 1000 --regions=123-456 paddr').split())
        err = _damon_args.deduce_target_update_args(args)
        self.assertEqual(err, None)
        ctx, err = _damon_args.damon_ctx_for(args)
        self.assertEqual(err, None)
        self.assertEqual(ctx, _damon.DamonCtx('paddr',
            [_damon.DamonTarget(None, [_damon.DamonRegion(123, 456)])],
            _damon.DamonIntervals(5000, 100000, 1000000),
            _damon.DamonNrRegionsRange(10, 1000), []))

        self.assertEqual(ctx, _damon.DamonCtx('paddr',
            [_damon.DamonTarget(None, [_damon.DamonRegion(123, 456)])],
            _damon.DamonIntervals(5000, 100000, 1000000),
            _damon.DamonNrRegionsRange(10, 1000), []))

        args = parser.parse_args(
                ('--sample 5ms --aggr 100ms --updr 1s ' +
                    '--minr 10 --maxr 1,000 --regions=1K-4K paddr').split())
        err = _damon_args.deduce_target_update_args(args)
        self.assertEqual(err, None)
        ctx, err = _damon_args.damon_ctx_for(args)
        self.assertEqual(err, None)
        self.assertEqual(ctx, _damon.DamonCtx('paddr',
            [_damon.DamonTarget(None, [_damon.DamonRegion(1024, 4096)])],
            _damon.DamonIntervals(5000, 100000, 1000000),
            _damon.DamonNrRegionsRange(10, 1000), []))

        parser = argparse.ArgumentParser()
        _damon_args.set_argparser(
                parser, add_record_options=False, min_help=True)

        args = parser.parse_args(
                ('--sample 5ms --aggr 100ms --updr 1s ' +
                    '--minr 10 --maxr 1,000 --regions=1K-4K ' +
                    '--ops paddr').split())
        ctx, err = _damon_args.damon_ctx_for(args)
        self.assertEqual(err, None)
        self.assertEqual(ctx, _damon.DamonCtx('paddr',
            [_damon.DamonTarget(None, [_damon.DamonRegion(1024, 4096)])],
            _damon.DamonIntervals(5000, 100000, 1000000),
            _damon.DamonNrRegionsRange(10, 1000), []))

    def test_damon_intervals_for(self):
        parser = argparse.ArgumentParser()
        _damon_args.set_monitoring_attrs_argparser(parser)
        _damon_args.set_monitoring_attrs_pinpoint_argparser(parser)

        args = parser.parse_args(
                '--monitoring_intervals 4ms 120ms 1.5s'.split())
        intervals = _damon_args.damon_intervals_for(args)
        self.assertEqual(intervals, _damon.DamonIntervals('4ms', '120ms',
            '1.5s'))

        args = parser.parse_args('--sample 7ms'.split())
        intervals = _damon_args.damon_intervals_for(args)
        self.assertEqual(intervals, _damon.DamonIntervals('7ms'))

    def test_damon_nr_regions_range_for(self):
        parser = argparse.ArgumentParser()
        _damon_args.set_monitoring_attrs_argparser(parser)
        _damon_args.set_monitoring_attrs_pinpoint_argparser(parser)

        args = parser.parse_args(
                '--monitoring_nr_regions_range 25 5000'.split())
        nr_range = _damon_args.damon_nr_regions_range_for(args)
        self.assertEqual(nr_range, _damon.DamonNrRegionsRange(25, 5000))

    def test_merge_cont_ranges(self):
        merged = _damon_args.merge_cont_ranges(
                [[10, 20], [25, 40], [40, 90], [90, 120], [125, 135],
                 [135, 150]])
        self.assertEqual(merged, [[10, 20], [25, 120], [125, 150]])

    def test_convert_add_damos_filter_out_args_to_damos_filter_args(self):
        args = argparse.Namespace(
                damos_filter=[
                    ['young', 'matching'],
                    ],
                damos_filter_out=[
                    ['anon'],
                    ['not', 'anon'],
                    ['memcg', '/path/to/a'],
                    ['not', 'memcg', '/path/to/a'],
                    ]
                )
        _damon_args.convert_add_damos_filter_out_args_to_damos_filter_args(
                args)
        self.assertEqual(args.damos_filter,
                         [
                             ['young', 'matching'],
                             ['anon', 'matching'],
                             ['anon', 'nomatching'],
                             ['memcg', 'matching', '/path/to/a'],
                             ['memcg', 'nomatching', '/path/to/a'],
                             ]
                         )

if __name__ == '__main__':
    unittest.main()
