#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import sys
import unittest

bindir = os.path.dirname(os.path.realpath(__file__))
damo_dir = os.path.join(bindir, '..', '..')
sys.path.append(damo_dir)

import _damon

class TestDamon(unittest.TestCase):
    def test_kvpairs_transition(self):
        target = _damon.DamonTarget('foo', 1234, [_damon.DamonRegion(10, 20)])
        target_kvpairs = target.to_kvpairs()
        target_again = _damon.kvpairs_to_DamonTarget(target_kvpairs)
        self.assertEqual(target, target_again)

        damos = _damon.Damos('foo',
                _damon.DamosAccessPattern(0, 10, 5, 8, 'percent', 54, 88,
                    'usec'),
                'pageout',
                _damon.DamosQuotas(100, 1024, 1000, 80, 76, 24),
                _damon.DamosWatermarks('free_mem_rate', 5000000, 800, 500,
                    200),
                [], None, None)
        damos_kvpairs = damos.to_kvpairs()
        damos_again = _damon.kvpairs_to_Damos(damos_kvpairs)
        self.assertEqual(damos, damos_again)

        ctx = _damon.DamonCtx('test_ctx',
                _damon.DamonIntervals(5000, 100000, 1000000),
                _damon.DamonNrRegionsRange(10, 1000),
                'paddr', [target], [damos])
        ctx_kvpairs = ctx.to_kvpairs()
        ctx_again = _damon.kvpairs_to_DamonCtx(ctx_kvpairs)
        self.assertEqual(ctx, ctx_again)


        kdamond = _damon.Kdamond('bar', 'off', 123, [ctx])
        kvpairs = kdamond.to_kvpairs()
        kdamond_again = _damon.kvpairs_to_Kdamond(kvpairs)
        self.assertEqual(kdamond, kdamond_again)

    def test_damos_eq(self):
        damos = _damon.Damos('0',
                access_pattern=_damon.DamosAccessPattern(4096,
                    18446744073709551615, 0.0, 0.0, 'percent', 1000000,
                    4294900000, 'usec'),
                action='stat',
                quotas=_damon.DamosQuotas(time_ms=0, sz_bytes=584792941,
                    reset_interval_ms=1000, weight_sz_permil=0,
                    weight_nr_accesses_permil=0, weight_age_permil=0),
                watermarks=_damon.DamosWatermarks(0,0,0,0,0),
                filters=[], stats=None)
        self.assertEqual(damos, damos)

    def test_kvpairs_to_damon_intervals(self):
        self.assertEqual(_damon.kvpairs_to_DamonIntervals(
            {'sample': 5000, 'aggr': 100000, 'ops_update': 1000000}),
            _damon.DamonIntervals(5000, 100000, 1000000))
        self.assertEqual(_damon.kvpairs_to_DamonIntervals(
            {'sample': '5ms', 'aggr': '0.1s', 'ops_update': '1s'}),
            _damon.DamonIntervals(5000, 100000, 1000000))

if __name__ == '__main__':
    unittest.main()
