#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json
import os
import sys
import unittest

import _test_damo_common

bindir = os.path.dirname(os.path.realpath(__file__))
damo_dir = os.path.join(bindir, '..', '..')
sys.path.append(damo_dir)

import _damon

class TestDamon(unittest.TestCase):
    def test_kvpairs_transition(self):
        target = _damon.DamonTarget('foo', 1234, [_damon.DamonRegion(10, 20)])
        self.assertEqual(target,
                _damon.kvpairs_to_DamonTarget(target.to_kvpairs()))

        damos = _damon.Damos('foo',
                _damon.DamosAccessPattern(0, 10, 5, 8, 'percent', 54, 88,
                    'usec'),
                'pageout',
                _damon.DamosQuotas(100, 1024, 1000, 80, 76, 24),
                _damon.DamosWatermarks('free_mem_rate', 5000000, 800, 500,
                    200),
                [], None, None)
        self.assertEqual(damos, _damon.kvpairs_to_Damos(damos.to_kvpairs()))

        ctx = _damon.DamonCtx('test_ctx',
                _damon.DamonIntervals(5000, 100000, 1000000),
                _damon.DamonNrRegionsRange(10, 1000),
                'paddr', [target], [damos])
        self.assertEqual(ctx, _damon.kvpairs_to_DamonCtx(ctx.to_kvpairs()))

        kdamond = _damon.Kdamond('bar', 'off', 123, [ctx])
        self.assertEqual(kdamond,
            _damon.kvpairs_to_Kdamond(kdamond.to_kvpairs()))

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

    def test_damon_intervals(self):
        _test_damo_common.test_input_expects(self,
                lambda x: _damon.kvpairs_to_DamonIntervals(json.loads(x)),
                {
                    json.dumps({'sample': 5000, 'aggr': 100000,
                        'ops_update': 1000000}):
                    _damon.DamonIntervals(5000, 100000, 1000000),
                    json.dumps({'sample': '5ms', 'aggr': '0.1s',
                        'ops_update': '1s'}):
                    _damon.DamonIntervals(5000, 100000, 1000000)})

        self.assertEqual('%s' % _damon.DamonIntervals(5000, 100000, 1000000),
        'sample 5 ms, aggr 100 ms, update 1 s')

        self.assertEqual(
                _damon.DamonIntervals(5000, 100000, 1000000).to_kvpairs(),
                {'sample': '5 ms', 'aggr': '100 ms', 'ops_update': '1 s'})

    def test_damon_nr_regions_range(self):
        expect = _damon.DamonNrRegionsRange(10, 1000)
        _test_damo_common.test_input_expects(self,
                lambda x: _damon.DamonNrRegionsRange(*x),
                {
                    tuple([10, '1000']): expect,
                    tuple(['10', '1000']): expect,
                    tuple(['10', '1,000']): expect})

        _test_damo_common.test_input_expects(self,
                lambda x: _damon.kvpairs_to_DamonNrRegionsRange(json.loads(x)),
                {
                    json.dumps({'min_nr_regions': 10, 'max_nr_regions': 1000}):
                    expect,
                    json.dumps(
                        {'min_nr_regions': '10', 'max_nr_regions': '1000'}):
                    expect,
                    json.dumps(
                        {'min_nr_regions': '10', 'max_nr_regions': '1,000'}):
                    expect})

        self.assertEqual('%s' % _damon.DamonNrRegionsRange(10, 1000),
                '[10, 1,000]')

        self.assertEqual(_damon.DamonNrRegionsRange(10, 1000).to_kvpairs(),
                {'min_nr_regions': '10', 'max_nr_regions': '1,000'})

    def test_damon_region(self):
        _test_damo_common.test_input_expects(self,
                lambda x: _damon.DamonRegion(*x),
                {
                    tuple([123, '456']): _damon.DamonRegion(123, 456),
                    tuple(['123', '456']): _damon.DamonRegion(123, 456),
                    tuple(['1,234', '4,567']): _damon.DamonRegion(1234, 4567)})

        _test_damo_common.test_input_expects(self,
                lambda x: _damon.kvpairs_to_DamonRegion(json.loads(x)),
                {
                    json.dumps({'start': '123', 'end': '456'}):
                    _damon.DamonRegion(123, 456),
                    json.dumps({'start': '1234', 'end': '4567'}):
                    _damon.DamonRegion(1234, 4567),
                    json.dumps({'start': '1,234', 'end': '4,567'}):
                    _damon.DamonRegion(1234, 4567)})

        self.assertEqual('%s' % _damon.DamonRegion(123, 456),
                '[123, 456) (333 B)')

        self.assertEqual(_damon.DamonRegion(1234, 5678).to_kvpairs(),
                {'start': '1,234', 'end': '5,678'})

if __name__ == '__main__':
    unittest.main()
