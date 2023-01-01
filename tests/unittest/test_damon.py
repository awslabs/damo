#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import collections
import copy
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
        target_kvpairs = target.to_kvpairs()
        self.assertEqual(type(target_kvpairs), collections.OrderedDict)
        self.assertEqual(list(target_kvpairs.keys()),
                ['name', 'pid', 'regions'])
        self.assertEqual(target,
                _damon.kvpairs_to_DamonTarget(target_kvpairs))

        damos = _damon.Damos('foo',
                _damon.DamosAccessPattern(0, 10, 5, 8, 'percent', 54, 88,
                    'usec'),
                'pageout',
                _damon.DamosQuotas(100, 1024, 1000, 80, 76, 24),
                _damon.DamosWatermarks('free_mem_rate', 5000000, 800, 500,
                    200),
                [], None, None)
        damos_kvpairs = damos.to_kvpairs()
        self.assertEqual(type(damos_kvpairs), collections.OrderedDict)
        self.assertEqual(list(damos_kvpairs.keys()),
                ['name', 'action', 'access_pattern', 'quotas', 'watermarks',
                    'filters'])
        self.assertEqual(damos, _damon.kvpairs_to_Damos(damos_kvpairs))

        ctx = _damon.DamonCtx('test_ctx',
                _damon.DamonIntervals(5000, 100000, 1000000),
                _damon.DamonNrRegionsRange(10, 1000),
                'paddr', [target], [damos])
        ctx_kvpairs = ctx.to_kvpairs()
        self.assertEqual(type(ctx_kvpairs), collections.OrderedDict)
        self.assertEqual(list(ctx_kvpairs.keys()),
                ['name', 'intervals', 'nr_regions', 'ops', 'targets',
                    'schemes'])
        self.assertEqual(ctx, _damon.kvpairs_to_DamonCtx(ctx_kvpairs))

        kdamond = _damon.Kdamond('bar', 'off', 123, [ctx])
        kdamond_kvpairs = kdamond.to_kvpairs()
        self.assertEqual(type(kdamond_kvpairs), collections.OrderedDict)
        self.assertEqual(list(kdamond_kvpairs.keys()),
                ['name', 'state', 'pid', 'contexts'])
        self.assertEqual(kdamond,
            _damon.kvpairs_to_Kdamond(kdamond_kvpairs))

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

        damos2 = _damon.Damos('0',
                access_pattern=_damon.DamosAccessPattern(4096,
                    18446744073709551615, 0.0, 0.0, 'percent', 1000000,
                    4294900000, 'usec'),
                action='stat',
                quotas=_damon.DamosQuotas(time_ms=0, sz_bytes=584792941,
                    reset_interval_ms=1000, weight_sz_permil=0,
                    weight_nr_accesses_permil=0, weight_age_permil=0),
                watermarks=_damon.DamosWatermarks(0,0,0,0,0),
                filters=[_damon.DamosFilter(name='foo', filter_type='memcg',
                    memcg_path='/foo/bar/', matching=True)], stats=None)
        self.assertFalse(damos == damos2)

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
        self.assertEqual('%s' %
                _damon.DamonIntervals(5000, 100000, 1000000).to_str(True),
                'sample 5000, aggr 100000, update 1000000')

        self.assertEqual(
                _damon.DamonIntervals(5000, 100000, 1000000).to_kvpairs(),
                {'sample': '5 ms', 'aggr': '100 ms', 'ops_update': '1 s'})
        self.assertEqual(
                _damon.DamonIntervals(
                    5000, 100000, 1000000).to_kvpairs(raw=True),
                {'sample': '5000', 'aggr': '100000', 'ops_update': '1000000'})

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
        self.assertEqual(
                '%s' % _damon.DamonNrRegionsRange(10, 1000).to_str(True),
                '[10, 1000]')

        self.assertEqual(_damon.DamonNrRegionsRange(10, 1000).to_kvpairs(),
                {'min_nr_regions': '10', 'max_nr_regions': '1,000'})
        self.assertEqual(_damon.DamonNrRegionsRange(10, 1000).to_kvpairs(
                        raw=True),
                {'min_nr_regions': '10', 'max_nr_regions': '1000'})

    def test_damon_region(self):
        _test_damo_common.test_input_expects(self,
                lambda x: _damon.DamonRegion(*x),
                {
                    tuple([123, '456']): _damon.DamonRegion(123, 456),
                    tuple(['123', '456']): _damon.DamonRegion(123, 456),
                    tuple(['1,234', '4,567']): _damon.DamonRegion(1234, 4567),
                    tuple(['1K', '4K']): _damon.DamonRegion(1024, 4096),
                    })

        _test_damo_common.test_input_expects(self,
                lambda x: _damon.kvpairs_to_DamonRegion(json.loads(x)),
                {
                    json.dumps({'start': '123', 'end': '456'}):
                    _damon.DamonRegion(123, 456),
                    json.dumps({'start': '1234', 'end': '4567'}):
                    _damon.DamonRegion(1234, 4567),
                    json.dumps({'start': '1,234', 'end': '4,567'}):
                    _damon.DamonRegion(1234, 4567),
                    json.dumps({'start': '1K', 'end': '4K'}):
                    _damon.DamonRegion(1024, 4096),
                    })

        self.assertEqual('%s' % _damon.DamonRegion(123, 456),
                '[123, 456) (333 B)')
        self.assertEqual('%s' % _damon.DamonRegion(123, 456).to_str(raw=True),
                '[123, 456) (333)')

        self.assertEqual(_damon.DamonRegion(1234, 5678).to_kvpairs(),
                {'start': '1,234', 'end': '5,678'})
        self.assertEqual(_damon.DamonRegion(1234, 5678).to_kvpairs(raw=True),
                {'start': '1234', 'end': '5678'})

    def test_damon_record(self):
        record_req = _damon.DamonRecord(4096, '/root/damon.data')
        self.assertEqual('%s' % record_req,
                'path: /root/damon.data, buffer sz: 4.000 KiB')

        self.assertEqual(record_req.to_kvpairs(raw=False),
                {'rfile_buf': 4096, 'rfile_path': '/root/damon.data'})

    def test_damos_access_pattern(self):
        intervals = _damon.DamonIntervals(5000, 100000, 1000000)
        pattern_human = _damon.DamosAccessPattern(123, 456,
                15, 35, 'percent', 5000000, 19000000, 'usec')
        pattern_machine = _damon.DamosAccessPattern(123, 456,
                3, 7, 'sample_intervals', 50, 190, 'aggr_intervals')

        self.assertEqual(
                pattern_human.converted_for_units(
                    'sample_intervals', 'aggr_intervals', intervals),
                pattern_machine)
        self.assertEqual(
                pattern_machine.converted_for_units(
                    'percent', 'usec', intervals),
                pattern_human)

if __name__ == '__main__':
    unittest.main()
