#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import collections
import copy
import json
import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damon

class TestDamon(unittest.TestCase):
    def test_kvpairs_transition(self):
        target = _damon.DamonTarget(1234, [_damon.DamonRegion(10, 20)])
        target_kvpairs = target.to_kvpairs()
        self.assertEqual(type(target_kvpairs), collections.OrderedDict)
        self.assertEqual(list(target_kvpairs.keys()),
                ['pid', 'regions'])
        self.assertEqual(target,
                _damon.DamonTarget.from_kvpairs(target_kvpairs))

        damos = _damon.Damos(
                _damon.DamosAccessPattern([0, 10], [5, 8], _damon.unit_percent,
                    [54, 88], _damon.unit_usec),
                'pageout',
                _damon.DamosQuotas(100, 1024, 1000, [80, 76, 24]),
                _damon.DamosWatermarks('free_mem_rate', 5000000, 800, 500,
                    200),
                [_damon.DamosFilter('memcg', '/foo/bar', True),
                    _damon.DamosFilter('anon', None, False)],
                    None, None)
        damos_kvpairs = damos.to_kvpairs()
        self.assertEqual(type(damos_kvpairs), collections.OrderedDict)
        self.assertEqual(list(damos_kvpairs.keys()),
                ['action', 'access_pattern', 'quotas', 'watermarks',
                    'filters'])
        self.assertEqual(damos, _damon.Damos.from_kvpairs(damos_kvpairs))

        ctx = _damon.DamonCtx(
                _damon.DamonIntervals(5000, 100000, 1000000),
                _damon.DamonNrRegionsRange(10, 1000),
                'paddr', [target], [damos])
        ctx_kvpairs = ctx.to_kvpairs()
        self.assertEqual(type(ctx_kvpairs), collections.OrderedDict)
        self.assertEqual(list(ctx_kvpairs.keys()),
                ['intervals', 'nr_regions', 'ops', 'targets',
                    'schemes'])
        self.assertEqual(ctx, _damon.DamonCtx.from_kvpairs(ctx_kvpairs))

        kdamond = _damon.Kdamond('off', 123, [ctx])
        kdamond_kvpairs = kdamond.to_kvpairs()
        self.assertEqual(type(kdamond_kvpairs), collections.OrderedDict)
        self.assertEqual(list(kdamond_kvpairs.keys()),
                ['state', 'pid', 'contexts'])
        self.assertEqual(kdamond,
            _damon.Kdamond.from_kvpairs(kdamond_kvpairs))

    def test_damos_default_immutable(self):
        damos = _damon.Damos()
        before = damos.quotas.time_ms
        damos.quotas.time_ms = 123
        damos = _damon.Damos()
        self.assertEqual(before, damos.quotas.time_ms)

    def test_damos_eq(self):
        damos = _damon.Damos(
                access_pattern=_damon.DamosAccessPattern([4096,
                    18446744073709551615], [0.0, 0.0], _damon.unit_percent,
                    [1000000, 4294900000], _damon.unit_usec),
                action='stat',
                quotas=_damon.DamosQuotas(time_ms=0, sz_bytes=584792941,
                    reset_interval_ms=1000, weights=[0,0,0]),
                watermarks=_damon.DamosWatermarks(0,0,0,0,0),
                filters=[], stats=None)
        damos2 = copy.deepcopy(damos)
        self.assertEqual(damos, damos2)

        damos2.filters = [_damon.DamosFilter(filter_type='memcg',
                    memcg_path='/foo/bar/', matching=True)]
        self.assertNotEqual(damos, damos2)

        intervals = _damon.DamonIntervals(5000, 100000, 1000000)
        pattern_human = _damon.DamosAccessPattern([123, 456],
                [15, 35], _damon.unit_percent,
                [5000000, 19000000], _damon.unit_usec)
        pattern_machine = _damon.DamosAccessPattern([123, 456],
                [3, 7], _damon.unit_sample_intervals,
                [50, 190], _damon.unit_aggr_intervals)

        damos.access_pattern = pattern_human
        damos2 = copy.deepcopy(damos)
        damos2.access_pattern = pattern_machine
        self.assertNotEqual(damos, damos2)
        self.assertTrue(damos.effectively_equal(damos2, intervals))
        self.assertTrue(damos.effectively_equal(damos2, intervals))

    def test_damos_action_validity(self):
        exception_raised = False
        try:
            _damon.Damos(action='foo')
        except:
            exception_raised = True
        self.assertTrue(exception_raised)
        for action in _damon.damos_actions:
            exception_raised = False
            try:
                _damon.Damos(action=action)
            except:
                exception_raised = True
            self.assertFalse(exception_raised)

    def test_damon_intervals(self):
        self.assertEqual(_damon.DamonIntervals(),
                _damon.DamonIntervals(5000, 100000, 1000000))

        _test_damo_common.test_input_expects(self,
                lambda x: _damon.DamonIntervals.from_kvpairs(json.loads(x)),
                {
                    json.dumps({'sample_us': 5000, 'aggr_us': 100000,
                        'ops_update_us': 1000000}):
                    _damon.DamonIntervals(5000, 100000, 1000000),
                    json.dumps({'sample_us': '5ms', 'aggr_us': '0.1s',
                        'ops_update_us': '1s'}):
                    _damon.DamonIntervals(5000, 100000, 1000000)})

        self.assertEqual('%s' % _damon.DamonIntervals(5000, 100000, 1000000),
        'sample 5 ms, aggr 100 ms, update 1 s')
        self.assertEqual('%s' %
                _damon.DamonIntervals(5000, 100000, 1000000).to_str(True),
                'sample 5000, aggr 100000, update 1000000')

        self.assertEqual(
                _damon.DamonIntervals(5000, 100000, 1000000).to_kvpairs(),
                {'sample_us': '5 ms', 'aggr_us': '100 ms',
                    'ops_update_us': '1 s'})
        self.assertEqual(
                _damon.DamonIntervals(
                    5000, 100000, 1000000).to_kvpairs(raw=True),
                {'sample_us': '5000', 'aggr_us': '100000',
                    'ops_update_us': '1000000'})

    def test_damon_nr_regions_range(self):
        self.assertEqual(_damon.DamonNrRegionsRange(),
                _damon.DamonNrRegionsRange(10, 1000))

        expect = _damon.DamonNrRegionsRange(10, 1000)
        _test_damo_common.test_input_expects(self,
                lambda x: _damon.DamonNrRegionsRange(*x),
                {
                    tuple([10, '1000']): expect,
                    tuple(['10', '1000']): expect,
                    tuple(['10', '1,000']): expect})

        _test_damo_common.test_input_expects(self,
                lambda x: _damon.DamonNrRegionsRange.from_kvpairs(
                    json.loads(x)),
                {
                    json.dumps({'min': 10, 'max': 1000}):
                    expect,
                    json.dumps(
                        {'min': '10', 'max': '1000'}):
                    expect,
                    json.dumps(
                        {'min': '10', 'max': '1,000'}):
                    expect})

        self.assertEqual('%s' % _damon.DamonNrRegionsRange(10, 1000),
                '[10, 1,000]')
        self.assertEqual(
                '%s' % _damon.DamonNrRegionsRange(10, 1000).to_str(True),
                '[10, 1000]')

        self.assertEqual(_damon.DamonNrRegionsRange(10, 1000).to_kvpairs(),
                {'min': '10', 'max': '1,000'})
        self.assertEqual(_damon.DamonNrRegionsRange(10, 1000).to_kvpairs(
                        raw=True),
                {'min': '10', 'max': '1000'})

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
                lambda x: _damon.DamonRegion.from_kvpairs(json.loads(x)),
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
        self.assertEqual(_damon.DamosAccessPattern(),
                _damon.DamosAccessPattern(['min', 'max'],
                    ['min', 'max'], _damon.unit_percent,
                    ['min', 'max'], _damon.unit_usec))

        intervals = _damon.DamonIntervals(5000, 100000, 1000000)
        pattern_human = _damon.DamosAccessPattern([123, '4,567'],
                [15, '10,000'], _damon.unit_percent,
                ['5,000,000', '190,000,000'], _damon.unit_usec)
        pattern_machine = _damon.DamosAccessPattern([123, 4567],
                [3, '2,000'], _damon.unit_sample_intervals,
                [50, '1,900'], _damon.unit_aggr_intervals)

        self.assertEqual(
                pattern_human.converted_for_units(
                    _damon.unit_sample_intervals,
                    _damon.unit_aggr_intervals, intervals),
                pattern_machine)
        self.assertEqual(
                pattern_machine.converted_for_units(
                    _damon.unit_percent, _damon.unit_usec, intervals),
                pattern_human)

        self.assertTrue(
                pattern_human.effectively_equal(pattern_machine, intervals))

        for converted in [
                pattern_human.converted_for_units(_damon.unit_sample_intervals,
                    _damon.unit_aggr_intervals, intervals),
                pattern_machine.converted_for_units(
                    _damon.unit_percent, _damon.unit_usec, intervals)]:
            self.assertEqual(type(converted.nr_accesses[0].value), int)
            self.assertEqual(type(converted.nr_accesses[1].value), int)
            self.assertEqual(type(converted.age[0].value), int)
            self.assertEqual(type(converted.age[1].value), int)

        exception_raised = False
        try:
            _damon.DamosAccessPattern(nr_accesses=[0, 100], nr_accesses_unit='foo')
        except:
            exception_raised = True
        self.assertTrue(exception_raised)
        exception_raised = False
        try:
            _damon.DamosAccessPattern(age=[0, 100], age_unit='bar')
        except:
            exception_raised = True
        self.assertTrue(exception_raised)

    def test_damos_quotas(self):
        self.assertEqual(_damon.DamosQuotas(),
                _damon.DamosQuotas(0, 0, 'max', [0, 0, 0]))

    def test_damos_watermarks(self):
        self.assertEqual(_damon.DamosWatermarks(),
                _damon.DamosWatermarks(_damon.damos_wmarks_metric_none,
                    0, 0, 0, 0))

    def test_damon_intervals_based_val_unit(self):
        intervals = _damon.DamonIntervals('5ms', '100ms', '1s')

        # for nr_accesses
        valunit = _damon.DamonIntervalsBasedValUnit(4,
                _damon.unit_sample_intervals)
        self.assertEqual(valunit.to_str(False),
                '%s %s' % (valunit.value, valunit.unit))

        self.assertEqual(valunit.value_for(_damon.unit_percent, intervals), 20)
        self.assertEqual(valunit.value, 4)

        valunit.convert_unit(_damon.unit_percent, intervals)
        self.assertEqual(valunit.value, 20)
        self.assertEqual(valunit.unit, _damon.unit_percent)
        self.assertEqual(valunit.to_str(False), '20 %')

        self.assertEqual(
                valunit.value_for(_damon.unit_sample_intervals, intervals), 4)
        self.assertEqual(valunit.value, 20)

        valunit.convert_unit(_damon.unit_sample_intervals, intervals)
        self.assertEqual(valunit.value, 4)
        self.assertEqual(valunit.unit, _damon.unit_sample_intervals)

        # for age
        valunit = _damon.DamonIntervalsBasedValUnit(15,
                _damon.unit_aggr_intervals)
        self.assertEqual(valunit.to_str(False),
                '%s %s' % (valunit.value, valunit.unit))

        valunit.convert_unit(_damon.unit_usec, intervals)
        self.assertEqual(valunit.value, 1500000)
        self.assertEqual(valunit.unit, _damon.unit_usec)
        self.assertEqual(valunit.to_str(False), '1 s 500 ms')

        valunit.convert_unit(_damon.unit_aggr_intervals, intervals)
        self.assertEqual(valunit.value, 15)
        self.assertEqual(valunit.unit, _damon.unit_aggr_intervals)

        self.assertEqual(
                _damon.DamonIntervalsBasedValUnit(42, _damon.unit_usec),
                _damon.DamonIntervalsBasedValUnit(42, _damon.unit_usec))
        self.assertNotEqual(
                _damon.DamonIntervalsBasedValUnit(42, _damon.unit_usec),
                _damon.DamonIntervalsBasedValUnit(43, _damon.unit_usec))
        self.assertNotEqual(
                _damon.DamonIntervalsBasedValUnit(42, _damon.unit_usec),
                _damon.DamonIntervalsBasedValUnit(42,
                    _damon.unit_aggr_intervals))

        self.assertTrue(
                _damon.DamonIntervalsBasedValUnit(
                    4, _damon.unit_sample_intervals).eq(
                        _damon.DamonIntervalsBasedValUnit(
                            20, _damon.unit_percent), intervals))
        self.assertFalse(
                _damon.DamonIntervalsBasedValUnit(
                    4, _damon.unit_sample_intervals).eq(
                        _damon.DamonIntervalsBasedValUnit(
                            25, _damon.unit_percent), intervals))
        self.assertTrue(
                _damon.DamonIntervalsBasedValUnit(
                    15, _damon.unit_aggr_intervals).eq(
                        _damon.DamonIntervalsBasedValUnit(
                            1500000, _damon.unit_usec), intervals))
        self.assertFalse(
                _damon.DamonIntervalsBasedValUnit(
                    15, _damon.unit_aggr_intervals).eq(
                        _damon.DamonIntervalsBasedValUnit(
                            160000, _damon.unit_usec), intervals))

if __name__ == '__main__':
    unittest.main()
