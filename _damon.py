#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON control.
"""

import collections
import copy
import os
import time

import _damo_fmt_str

# Core data structures

class DamonIntervals:
    sample = None
    aggr = None
    ops_update = None

    def __init__(self, sample='5ms', aggr='100ms', ops_update='1s'):
        self.sample = _damo_fmt_str.text_to_us(sample)
        self.aggr = _damo_fmt_str.text_to_us(aggr)
        self.ops_update = _damo_fmt_str.text_to_us(ops_update)

    def to_str(self, raw):
        return 'sample %s, aggr %s, update %s' % (
                _damo_fmt_str.format_time_us(self.sample, raw),
                _damo_fmt_str.format_time_us(self.aggr, raw),
                _damo_fmt_str.format_time_us(self.ops_update, raw))

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return type(self) == type(other) and '%s' % self == '%s' % other

    @classmethod
    def from_kvpairs(cls, kvpairs):
        return DamonIntervals(
                kvpairs['sample_us'], kvpairs['aggr_us'],
                kvpairs['ops_update_us'])

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict([
            ('sample_us', _damo_fmt_str.format_time_us(self.sample, raw)),
            ('aggr_us', _damo_fmt_str.format_time_us(self.aggr, raw)),
            ('ops_update_us',
                _damo_fmt_str.format_time_us(self.ops_update, raw)),
            ])

class DamonNrRegionsRange:
    minimum = None
    maximum = None

    def __init__(self, min_=10, max_=1000):
        self.minimum = _damo_fmt_str.text_to_nr(min_)
        self.maximum = _damo_fmt_str.text_to_nr(max_)

    def to_str(self, raw):
        return '[%s, %s]' % (
                _damo_fmt_str.format_nr(self.minimum, raw),
                _damo_fmt_str.format_nr(self.maximum, raw))

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return type(self) == type(other) and '%s' % self == '%s' % other

    @classmethod
    def from_kvpairs(cls, kvpairs):
        return DamonNrRegionsRange(kvpairs['min'], kvpairs['max'])

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict([
            ('min', _damo_fmt_str.format_nr(self.minimum, raw)),
            ('max', _damo_fmt_str.format_nr(self.maximum, raw)),
            ])

class DamonRegion:
    # [star, end)
    start = None
    end = None

    def __init__(self, start, end):
        self.start = _damo_fmt_str.text_to_bytes(start)
        self.end = _damo_fmt_str.text_to_bytes(end)

    def to_str(self, raw):
        return _damo_fmt_str.format_addr_range(self.start, self.end, raw)

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return type(self) == type(other) and '%s' % self == '%s' % other

    @classmethod
    def from_kvpairs(cls, kvpairs):
        return DamonRegion(kvpairs['start'], kvpairs['end'])

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict([
            ('start', _damo_fmt_str.format_nr(self.start, raw)),
            ('end', _damo_fmt_str.format_nr(self.end, raw))])

class DamonTarget:
    name = None
    pid = None
    regions = None

    def __init__(self, name, pid, regions):
        self.name = name
        self.pid = pid
        self.regions = regions

    def to_str(self, raw):
        lines = ['%s (pid: %s)' % (self.name, self.pid)]
        for region in self.regions:
            lines.append('region %s' % region.to_str(raw))
        return '\n'.join(lines)

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return type(self) == type(other) and '%s' % self == '%s' % other

    @classmethod
    def from_kvpairs(cls, kvpairs):
        regions = [DamonRegion.from_kvpairs(kvp) for kvp in kvpairs['regions']]
        return DamonTarget(kvpairs['name'], kvpairs['pid'], regions)

    def to_kvpairs(self, raw=False):
        kvp = collections.OrderedDict(
                [(attr, getattr(self, attr)) for attr in ['name', 'pid']])
        kvp['regions'] = [r.to_kvpairs(raw) for r in self.regions]
        return kvp

unit_percent = 'percent'
unit_sample_intervals = 'sample_intervals'
unit_usec = 'usec'
unit_aggr_intervals = 'aggr_intervals'

class DamosAccessPattern:
    sz_bytes = None
    nr_accesses = None
    nr_accesses_unit = None # unit_{percent,sample_intervals}
    age = None
    age_unit = None #  unit_{usec,aggr_intervals}

    # every region by default, so that it can be used for monitoring
    def __init__(self, sz_bytes=['min', 'max'],
            nr_accesses=['min', 'max'], nr_accesses_unit=unit_percent,
            age=['min', 'max'], age_unit=unit_usec):
        self.sz_bytes = [_damo_fmt_str.text_to_bytes(sz_bytes[0]),
                _damo_fmt_str.text_to_bytes(sz_bytes[1])]

        if nr_accesses_unit == unit_percent:
            fn = _damo_fmt_str.text_to_percent
        elif nr_accesses_unit == unit_sample_intervals:
            fn = _damo_fmt_str.text_to_nr
        else:
            raise Exception('invalid access pattern nr_accesses_unit \'%s\'' %
                    nr_accesses_unit)
        self.nr_accesses = [fn(nr_accesses[0]), fn(nr_accesses[1])]
        self.nr_accesses_unit = nr_accesses_unit

        if age_unit == unit_usec:
            fn = _damo_fmt_str.text_to_us
        elif age_unit == unit_aggr_intervals:
            fn = _damo_fmt_str.text_to_nr
        else:
            raise Exception('invalid access pattern age_unit \'%s\'' %
                    age_unit)
        self.age = [fn(age[0]), fn(age[1])]
        self.age_unit = age_unit

    def to_str(self, raw):
        lines = [
            'sz: [%s, %s]' % (_damo_fmt_str.format_sz(self.sz_bytes[0], raw),
                _damo_fmt_str.format_sz(self.sz_bytes[1], raw)),
            ]
        unit = self.nr_accesses_unit
        if unit == unit_percent:
            unit = '%'
        lines.append('nr_accesses: [%s %s, %s %s]' % (
                _damo_fmt_str.format_nr(self.nr_accesses[0], raw), unit,
                _damo_fmt_str.format_nr(self.nr_accesses[1], raw), unit))
        if self.age_unit == unit_usec:
            min_age = _damo_fmt_str.format_time_us_exact(self.age[0], raw)
            max_age = _damo_fmt_str.format_time_us_exact(self.age[1], raw)
        else:
            min_age = '%s %s' % (
                    _damo_fmt_str.format_nr(self.age[0], raw), self.age_unit)
            max_age = '%s %s' % (
                    _damo_fmt_str.format_nr(self.age[1], raw), self.age_unit)
        lines.append('age: [%s, %s]' % (min_age, max_age))
        return '\n'.join(lines)

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.sz_bytes == other.sz_bytes and
                self.nr_accesses == other.nr_accesses and
                self.nr_accesses_unit == other.nr_accesses_unit and
                self.age == other.age and self.age_unit == other.age_unit)

    @classmethod
    def from_kvpairs(cls, kv):
        sz_bytes = [_damo_fmt_str.text_to_bytes(kv['sz_bytes']['min']),
                _damo_fmt_str.text_to_bytes(kv['sz_bytes']['max'])]

        kv_ = kv['nr_accesses']
        try:
            nr_accesses = [_damo_fmt_str.text_to_percent(kv_['min']),
                    _damo_fmt_str.text_to_percent(kv_['max'])]
            nr_accesses_unit = unit_percent
        except:
            min_, nr_accesses_unit = _damo_fmt_str.text_to_nr_unit(kv_['min'])
            max_, nr_accesses_unit2 = _damo_fmt_str.text_to_nr_unit(kv_['max'])
            if nr_accesses_unit != nr_accesses_unit2:
                raise Exception('nr_accesses units should be same')
            nr_accesses = [min_, max_]

        kv_ = kv['age']
        try:
            age = [_damo_fmt_str.text_to_us(kv_['min']),
                    _damo_fmt_str.text_to_us(kv_['max'])]
            age_unit = unit_usec
        except:
            min_age, age_unit = _damo_fmt_str.text_to_nr_unit(kv_['min'])
            max_age, age_unit2 = _damo_fmt_str.text_to_nr_unit(kv_['max'])
            if age_unit != age_unit2:
                raise Exception('age units should be same')
            age = [min_age, max_age]

        return DamosAccessPattern(sz_bytes, nr_accesses, nr_accesses_unit, age,
                age_unit)

    def to_kvpairs(self, raw=False):
        unit = self.nr_accesses_unit
        if unit == unit_percent:
            unit = '%'
        min_nr_accesses = '%s %s' % (
                _damo_fmt_str.format_nr(self.nr_accesses[0], raw), unit)
        max_nr_accesses = '%s %s' % (
                _damo_fmt_str.format_nr(self.nr_accesses[1], raw), unit)
        if self.age_unit == unit_usec:
            min_age = _damo_fmt_str.format_time_us_exact(self.age[0], raw)
            max_age = _damo_fmt_str.format_time_us_exact(self.age[1], raw)
        else:
            min_age = '%s %s' % (
                    _damo_fmt_str.format_nr(self.age[0], raw), self.age_unit)
            max_age = '%s %s' % (
                    _damo_fmt_str.format_nr(self.age[1], raw), self.age_unit)

        return collections.OrderedDict([
            ('sz_bytes', (collections.OrderedDict([
                ('min', _damo_fmt_str.format_sz(self.sz_bytes[0], raw)),
                ('max', _damo_fmt_str.format_sz(self.sz_bytes[1], raw))]))),
            ('nr_accesses', (collections.OrderedDict([
                ('min', min_nr_accesses), ('max', max_nr_accesses)]))),
            ('age', (collections.OrderedDict([
                ('min', min_age), ('max', max_age)]))),
            ])

    def convert_nr_accesses_unit(self, nr_accesses_unit, intervals):
        if self.nr_accesses_unit == nr_accesses_unit:
            return
        max_nr_accesses_sample_intervals = intervals.aggr / intervals.sample
        # percent to sample_intervals
        if nr_accesses_unit == unit_sample_intervals:
            self.nr_accesses[0] = int(self.nr_accesses[0] *
                    max_nr_accesses_sample_intervals / 100)
            self.nr_accesses[1] = int(self.nr_accesses[1] *
                    max_nr_accesses_sample_intervals / 100)
        # sample_intervals to percent
        else:
            self.nr_accesses[0] = int(self.nr_accesses[0] * 100.0 /
                    max_nr_accesses_sample_intervals)
            self.nr_accesses[1] = int(self.nr_accesses[1] * 100.0 /
                    max_nr_accesses_sample_intervals)
        self.nr_accesses_unit = nr_accesses_unit

    def convert_age_unit(self, age_unit, intervals):
        if self.age_unit == age_unit:
            return
        # aggr_intervals to usec
        if age_unit == unit_usec:
            self.age[0] = self.age[0] * intervals.aggr
            self.age[1] = self.age[1] * intervals.aggr
        # usec to aggr_intervals
        else:
            self.age[0] = int(self.age[0] / intervals.aggr)
            self.age[1] = int(self.age[1] / intervals.aggr)
        self.age_unit = age_unit

    def convert_for_units(self, nr_accesses_unit, age_unit, intervals):
        self.convert_nr_accesses_unit(nr_accesses_unit, intervals)
        self.convert_age_unit(age_unit, intervals)

    def converted_for_units(self, nr_accesses_unit, age_unit, intervals):
        copied = copy.deepcopy(self)
        copied.convert_for_units(nr_accesses_unit, age_unit, intervals)
        return copied

    def effectively_equal(self, other, intervals):
        return (
                self.converted_for_units(
                    unit_sample_intervals, unit_aggr_intervals, intervals) ==
                other.converted_for_units(
                    unit_sample_intervals, unit_aggr_intervals, intervals))

class DamosQuotas:
    time_ms = None
    sz_bytes = None
    reset_interval_ms = None
    weight_sz_permil = None
    weight_nr_accesses_permil = None
    weight_age_permil = None

    def __init__(self, time_ms=0, sz_bytes=0, reset_interval_ms='max',
            weights=['0 %', '0 %', '0 %']):
        self.time_ms = _damo_fmt_str.text_to_ms(time_ms)
        self.sz_bytes = _damo_fmt_str.text_to_bytes(sz_bytes)
        self.reset_interval_ms = _damo_fmt_str.text_to_ms(reset_interval_ms)
        self.weight_sz_permil = _damo_fmt_str.text_to_permil(weights[0])
        self.weight_nr_accesses_permil = _damo_fmt_str.text_to_permil(
                weights[1])
        self.weight_age_permil = _damo_fmt_str.text_to_permil(weights[2])

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return (type(self) == type(other) and self.time_ms == other.time_ms and
                self.sz_bytes == other.sz_bytes and self.reset_interval_ms ==
                other.reset_interval_ms and self.weight_sz_permil ==
                other.weight_sz_permil and self.weight_nr_accesses_permil ==
                other.weight_nr_accesses_permil and self.weight_age_permil ==
                other.weight_age_permil)

    @classmethod
    def from_kvpairs(cls, kv):
        return DamosQuotas(kv['time_ms'], kv['sz_bytes'],
                kv['reset_interval_ms'],
                [kv['weights']['sz_permil'],
                    kv['weights']['nr_accesses_permil'],
                    kv['weights']['age_permil'],])

    def to_str(self, raw):
        return '\n'.join([
            '%s / %s per %s' % (
                _damo_fmt_str.format_sz(self.time_ms * 1000000, raw),
                _damo_fmt_str.format_time_ns(self.sz_bytes, raw),
                _damo_fmt_str.format_time_ms(self.reset_interval_ms, raw)),
            'priority: sz %s, nr_accesses %s, age %s' % (
                _damo_fmt_str.format_permil(self.weight_sz_permil, raw),
                _damo_fmt_str.format_permil(
                    self.weight_nr_accesses_permil, raw),
                _damo_fmt_str.format_permil(self.weight_age_permil, raw)),
            ])

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict([
            ('time_ms', _damo_fmt_str.format_time_ms_exact(self.time_ms, raw)),
            ('sz_bytes', _damo_fmt_str.format_sz(self.sz_bytes, raw)),
            ('reset_interval_ms', _damo_fmt_str.format_time_ms_exact(
                self.reset_interval_ms, raw)),
            ('weights', (collections.OrderedDict([
                ('sz_permil',
                    _damo_fmt_str.format_permil(self.weight_sz_permil, raw)),
                ('nr_accesses_permil', _damo_fmt_str.format_permil(
                    self.weight_nr_accesses_permil, raw)),
                ('age_permil',
                    _damo_fmt_str.format_permil(self.weight_age_permil, raw))])
                ))])

damos_wmarks_metric_none = 'none'
damos_wmarks_metric_free_mem_rate = 'free_mem_rate'

class DamosWatermarks:
    metric = None
    interval_us = None
    high_permil = None
    mid_permil = None
    low_permil = None

    # no limit by default
    def __init__(self, metric=damos_wmarks_metric_none, interval_us=0,
            high='0 %', mid='0 %', low='0 %'):
        # 'none' or 'free_mem_rate'
        self.metric = metric
        self.interval_us = _damo_fmt_str.text_to_us(interval_us)
        self.high_permil = _damo_fmt_str.text_to_permil(high)
        self.mid_permil = _damo_fmt_str.text_to_permil(mid)
        self.low_permil = _damo_fmt_str.text_to_permil(low)

    def to_str(self, raw):
        return '\n'.join([
            '%s/%s/%s' % (
                _damo_fmt_str.format_permil(self.high_permil, raw),
                _damo_fmt_str.format_permil(self.mid_permil, raw),
                _damo_fmt_str.format_permil(self.low_permil, raw)),
            'metric %s, interval %s' % (self.metric,
                _damo_fmt_str.format_time_us(self.interval_us, raw))
            ])

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return (type(self) == type(other) and self.metric == other.metric and
                self.interval_us == other.interval_us and
                self.high_permil == other.high_permil and
                self.mid_permil == other.mid_permil and
                self.low_permil == other.low_permil)

    @classmethod
    def from_kvpairs(cls, kv):
        return DamosWatermarks(*[kv[x] for x in
            ['metric', 'interval_us', 'high_permil', 'mid_permil',
                'low_permil']])

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict([
                ('metric', self.metric),
                ('interval_us', _damo_fmt_str.format_time_us_exact(
                    self.interval_us, raw)),
                ('high_permil',
                    _damo_fmt_str.format_permil(self.high_permil, raw)),
                ('mid_permil',
                    _damo_fmt_str.format_permil(self.mid_permil, raw)),
                ('low_permil',
                    _damo_fmt_str.format_permil(self.low_permil, raw)),
                ])

class DamosFilter:
    name = None
    filter_type = None  # anon or memcg
    memcg_path = None
    matching = None

    def __init__(self, name, filter_type, memcg_path, matching):
        self.name = name
        self.filter_type = filter_type
        self.memcg_path = memcg_path
        self.matching = _damo_fmt_str.text_to_bool(matching)

    def to_str(self, raw):
        memcg_path_str = ''
        if self.filter_type == 'memcg':
            memcg_path_str = 'memcg_path %s, ' % self.memcg_path
        return 'filter_type %s, %smatching %s' % (
                self.filter_type, memcg_path_str, self.matching)

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return type(self) == type(other) and '%s' % self == '%s' % other

    @classmethod
    def from_kvpairs(cls, kv):
        return DamosFilter(kv['name'], kv['filter_type'],
                kv['memcg_path'] if kv['filter_type'] == 'memcg' else '',
                kv['matching'])

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict(
                [(attr, getattr(self, attr)) for attr in [
                    'name', 'filter_type', 'memcg_path', 'matching']])

class DamosStats:
    nr_tried = None
    sz_tried = None
    nr_applied = None
    sz_applied = None
    qt_exceeds = None

    def __init__(self, nr_tried, sz_tried, nr_applied, sz_applied, qt_exceeds):
        self.nr_tried = nr_tried
        self.sz_tried = sz_tried
        self.nr_applied = nr_applied
        self.sz_applied = sz_applied
        self.qt_exceeds = qt_exceeds

    def to_str(self, raw):
        return '\n'.join([
            'tried %d times (%s)' % (self.nr_tried,
            _damo_fmt_str.format_sz(self.sz_tried, raw)),
            'applied %d times (%s)' % (self.nr_applied,
            _damo_fmt_str.format_sz(self.sz_applied, raw)),
            'quota exceeded %d times' % self.qt_exceeds,
            ])

    def __str__(self):
        return self.to_str(False)

class DamosTriedRegion:
    start = None
    end = None
    nr_accesses = None
    age = None

    def __init__(self, start, end, nr_accesses, age):
        self.start = start
        self.end = end
        self.nr_accesses = nr_accesses
        self.age = age

    def to_str(self, raw, intervals=None):
        age = self.age
        if raw == False and intervals != None:
            max_nr_accesses = intervals.aggr / intervals.sample
            nr_accesses = '%.2f%%' % (
                    float(self.nr_accesses) * 100 / max_nr_accesses)
            age = _damo_fmt_str.format_time_us(age * intervals.aggr, raw)
        else:
            nr_accesses = '%s' % _damo_fmt_str.format_nr(self.nr_accesses, raw)
            age = _damo_fmt_str.format_nr(age, raw)
        return '%s: nr_accesses: %s, age: %s' % (
                _damo_fmt_str.format_addr_range(self.start, self.end, raw),
                nr_accesses, age)

    def __str__(self):
        return self.to_str(False)

# TODO: check support of pageout and lru_(de)prio
damos_actions = [
        'willneed',
        'cold',
        'pageout',
        'hugepage',
        'nohugepage',
        'lru_prio',
        'lru_deprio',
        'stat',
        ]

damos_action_willneed = damos_actions[0]
damos_action_cold = damos_actions[1]
damos_action_pageout = damos_actions[2]
damos_action_hugepage = damos_actions[3]
damos_action_nohugepage = damos_actions[4]
damos_action_lru_prio = damos_actions[5]
damos_action_lru_deprio = damos_actions[6]
damos_action_stat = damos_actions[7]

class Damos:
    name = None
    access_pattern = None
    action = None
    quotas = None
    watermarks = None
    filters = None
    stats = None
    tried_regions = None

    # for monitoring only by default
    def __init__(self, name='0', access_pattern=None, action=damos_action_stat,
            quotas=None, watermarks=None, filters=None, stats=None,
            tried_regions=None):
        self.name = name
        self.access_pattern = (access_pattern
                if access_pattern != None else DamosAccessPattern())
        if not action in damos_actions:
            raise Exception('wrong damos action: %s' % action)
        self.action = action
        self.quotas = quotas if quotas != None else DamosQuotas()
        self.watermarks = (watermarks
                if watermarks != None else DamosWatermarks())
        self.filters = filters if filters != None else []
        self.stats = stats
        self.tried_regions = tried_regions

    def to_str(self, raw):
        lines = ['%s (action: %s)' % (self.name, self.action)]
        lines.append('target access pattern')
        lines.append(_damo_fmt_str.indent_lines(
            self.access_pattern.to_str(raw), 4))
        lines.append('quotas')
        lines.append(_damo_fmt_str.indent_lines(self.quotas.to_str(raw), 4))
        lines.append('watermarks')
        lines.append(_damo_fmt_str.indent_lines(
            self.watermarks.to_str(raw), 4))
        lines.append('filters')
        for damos_filter in self.filters:
            lines.append(_damo_fmt_str.indent_lines(
                damos_filter.to_str(raw), 8))
        if self.stats != None:
            lines.append('statistics')
            lines.append(_damo_fmt_str.indent_lines(self.stats.to_str(raw), 4))
        if self.tried_regions != None:
            lines.append('tried regions')
            for region in self.tried_regions:
                lines.append(_damo_fmt_str.indent_lines(region.to_str(raw), 4))
        return '\n'.join(lines)

    def __str__(self):
        return self.to_str(False)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return (type(self) == type(other) and self.name == other.name and
                self.access_pattern == other.access_pattern and
                self.action == other.action and self.quotas == other.quotas and
                self.watermarks == other.watermarks and
                self.filters == other.filters)

    @classmethod
    def from_kvpairs(cls, kv):
        filters = []
        if 'filters' in kv:
            for damos_filter_kv in kv['filters']:
                filters.append(DamosFilter.from_kvpairs(damos_filter_kv))
        return Damos(kv['name'] if 'name' in kv else '0',
                DamosAccessPattern.from_kvpairs(kv['access_pattern'])
                    if 'access_pattern' in kv else DamosAccessPattern(),
                kv['action'] if 'action' in kv else damos_action_stat,
                DamosQuotas.from_kvpairs(kv['quotas'])
                    if 'quotas' in kv else DamosQuotas(),
                DamosWatermarks.from_kvpairs(kv['watermarks'])
                    if 'watermarks' in kv else DamosWatermarks(),
                filters,
                None, None)

    def to_kvpairs(self, raw=False):
        kv = collections.OrderedDict(
                [(attr, getattr(self, attr)) for attr in ['name', 'action']])
        kv['access_pattern'] = self.access_pattern.to_kvpairs(raw)
        kv['quotas'] = self.quotas.to_kvpairs(raw)
        kv['watermarks'] = self.watermarks.to_kvpairs(raw)
        filters = []
        for damos_filter in self.filters:
            filters.append(damos_filter.to_kvpairs(raw))
        kv['filters'] = filters
        return kv

    def effectively_equal(self, other, intervals):
        return (type(self) == type(other) and
                self.access_pattern.effectively_equal(
                    other.access_pattern, intervals) and
                self.action == other.action and self.quotas == other.quotas and
                self.watermarks == other.watermarks and
                self.filters == other.filters)

def is_monitoring_scheme(scheme, intervals):
    return Damos().effectively_equal(scheme, intervals)

class DamonRecord:
    rfile_buf = None
    rfile_path = None

    def __init__(self, rfile_buf, rfile_path):
        self.rfile_buf = _damo_fmt_str.text_to_bytes(rfile_buf)
        self.rfile_path = rfile_path

    def to_str(self, raw):
        return 'path: %s, buffer sz: %s' % (self.rfile_path,
                _damo_fmt_str.format_sz(self.rfile_buf, raw))

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return type(self) == type(other) and '%s' % self == '%s' % other

    @classmethod
    def from_kvpairs(cls, kv):
        return DamonRecord(kv['rfile_buf'], kv['rfile_path'])

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict(
                [(attr, getattr(self, attr)) for attr in
                    ['rfile_buf', 'rfile_path']])

class DamonCtx:
    name = None
    intervals = None
    nr_regions = None
    ops = None
    targets = None
    schemes = None
    # For old downstream kernels that supports record feature
    record_request = None

    def __init__(self, name, intervals, nr_regions, ops, targets, schemes,
            record_request=None):
        self.name = name
        self.intervals = intervals
        self.nr_regions = nr_regions
        self.ops = ops
        self.targets = targets
        self.schemes = schemes
        self.record_request = record_request

    def to_str(self, raw):
        lines = ['%s (ops: %s)' % (self.name, self.ops)]
        lines.append('intervals: %s' % self.intervals.to_str(raw))
        lines.append('nr_regions: %s' % self.nr_regions.to_str(raw))
        lines.append('targets')
        for target in self.targets:
            lines.append(_damo_fmt_str.indent_lines(target.to_str(raw), 4))
        lines.append('schemes')
        for scheme in self.schemes:
            lines.append(_damo_fmt_str.indent_lines(scheme.to_str(raw), 4))
        return '\n'.join(lines)

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return type(self) == type(other) and '%s' % self == '%s' % other

    def __hash__(self):
        return hash(self.__str__())

    @classmethod
    def from_kvpairs(cls, kv):
        ctx = DamonCtx(kv['name'],
                DamonIntervals.from_kvpairs(kv['intervals'])
                    if 'intervals' in kv else DamonIntervals(),
                DamonNrRegionsRange.from_kvpairs(kv['nr_regions'])
                    if 'nr_regions' in kv else DAmonNrRegionsRange(),
                kv['ops'],
                [DamonTarget.from_kvpairs(t) for t in kv['targets']],
                [Damos.from_kvpairs(s) for s in kv['schemes']]
                    if 'schemes' in kv else [])
        if 'record_request' in kv:
            ctx.record_request = DamonRecord.from_kvpairs(kv['record_request'])
        return ctx

    def to_kvpairs(self, raw=False):
        kv = collections.OrderedDict({})
        kv['name'] = self.name
        kv['intervals'] = self.intervals.to_kvpairs(raw)
        kv['nr_regions'] = self.nr_regions.to_kvpairs(raw)
        kv['ops'] = self.ops
        kv['targets'] = [t.to_kvpairs(raw) for t in self.targets]
        kv['schemes'] = [s.to_kvpairs(raw) for s in self.schemes]
        if self.record_request:
            kv['record_request'] = self.record_request.to_kvpairs(raw)
        return kv

def target_has_pid(ops):
    return ops in ['vaddr', 'fvaddr']

class Kdamond:
    name = None
    state = None
    pid = None
    contexts = None

    def __init__(self, name, state, pid, contexts):
        self.name = name
        self.state = state
        self.pid = pid
        self.contexts = contexts

    def summary_str(self):
        return '%s (state: %s, pid: %s)' % (self.name, self.state, self.pid)

    def to_str(self, raw):
        lines = [self.summary_str()]
        for ctx in self.contexts:
            lines.append('contexts')
            lines.append(_damo_fmt_str.indent_lines(ctx.to_str(raw), 4))
        return '\n'.join(lines)

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return type(self) == type(other) and '%s' % self == '%s' % other

    def __hash__(self):
        return hash(self.__str__())

    @classmethod
    def from_kvpairs(cls, kv):
        return Kdamond(kv['name'],
                kv['state'] if 'state' in kv else 'off',
                kv['pid'] if 'pid' in kv else None,
                [DamonCtx.from_kvpairs(c) for c in kv['contexts']])

    def to_kvpairs(self, raw=False):
        kv = collections.OrderedDict()
        kv['name'] = self.name
        kv['state'] = self.state
        kv['pid'] = self.pid
        kv['contexts'] = [c.to_kvpairs(raw) for c in self.contexts]
        return kv

import _damo_fs
import _damon_dbgfs
import _damon_sysfs

# System check

features = ['record',       # was in DAMON patchset, but not merged in mainline
            'vaddr',        # merged in v5.15, thebeginning
            'schemes',      # merged in v5.16
            'init_regions', # merged in v5.16 (90bebce9fcd6)
            'paddr',        # merged in v5.16 (a28397beb55b)
            'schemes_speed_limit',      # merged in v5.16 (2b8a248d5873)
            'schemes_quotas',           # merged in v5.16 (1cd243030059)
            'schemes_prioritization',   # merged in v5.16 (38683e003153)
            'schemes_wmarks',           # merged in v5.16 (ee801b7dd782)
            'schemes_stat_succ',        # merged in v5.17 (0e92c2ee9f45)
            'schemes_stat_qt_exceed',   # merged in v5.17 (0e92c2ee9f45)
            'init_regions_target_idx',  # merged in v5.18 (144760f8e0c3)
            'fvaddr',       # merged in v5.19 (b82434471cd2)
            'schemes_tried_regions',    # merged in v6.2-rc1
            'schemes_filters',          # merged in mm-unstable
            'schemes_tried_regions_sz', # developing
            ]

_damon_fs = None

pr_debug_log = False

def ensure_root_permission():
    if os.geteuid() != 0:
        print('Run as root')
        exit(1)

def feature_supported(feature):
    return _damon_fs.feature_supported(feature)

def initialize(args):
    global _damon_fs
    if args.damon_interface == 'sysfs':
        _damon_fs = _damon_sysfs
    elif args.damon_interface == 'debugfs':
        _damon_fs = _damon_dbgfs
    elif args.damon_interface == 'auto':
        if _damon_sysfs.supported():
            _damon_fs = _damon_sysfs
        else:
            _damon_fs = _damon_dbgfs

    global pr_debug_log
    if args.debug_damon:
        pr_debug_log = True

    return _damon_fs.update_supported_features()

initialized = False
def ensure_initialized(args):
    global initialized

    if initialized:
        return
    err = initialize(args)
    if err != None:
        print(err)
        exit(1)
    initialized = True

def ensure_root_and_initialized(args):
    ensure_root_permission()
    ensure_initialized(args)

def damon_interface():
    if _damon_fs == _damon_sysfs:
        return 'sysfs'
    elif _damon_fs == _damon_dbgfs:
        return 'debugfs'
    raise Exception('_damo_fs is neither _damon_sysfs nor _damon_dbgfs')

# DAMON status reading

def is_kdamond_running(kdamond_name):
    return _damon_fs.is_kdamond_running(kdamond_name)

def current_kdamonds():
    return _damon_fs.current_kdamonds()

def current_kdamond_names():
    return _damon_fs.current_kdamond_names()

def running_kdamonds():
    return [k for k in current_kdamonds() if k.state == 'on']

def running_kdamond_names():
    return [name for name in current_kdamond_names()
            if is_kdamond_running(name)]

def any_kdamond_running():
    for kd_name in current_kdamond_names():
        if is_kdamond_running(kd_name):
            return True
    return False

def every_kdamond_turned_off():
    return not any_kdamond_running()

def wait_current_kdamonds_turned_on():
    for kd_name in current_kdamond_names():
        while not is_kdamond_running(kd_name):
            time.sleep(1)

def wait_current_kdamonds_turned_off():
    for kd_name in current_kdamond_names():
        while is_kdamond_running(kd_name):
            time.sleep(1)

# DAMON control

def stage_kdamonds(kdamonds):
    return _damon_fs.stage_kdamonds(kdamonds)

def commit_staged(kdamond_names):
    if _damon_fs == _damon_dbgfs:
        return 'debugfs interface unsupport commit_staged()'
    return _damon_fs.commit_staged(kdamond_names)

def commit(kdamonds):
    err = stage_kdamonds(kdamonds)
    if err:
        return 'staging updates failed (%s)' % err
    err = commit_staged([k.name for k in kdamonds])
    if err:
        return 'commit staged updates filed (%s)' % err
    return None

def update_schemes_stats(kdamond_names=None):
    if kdamond_names == None:
        kdamond_names = running_kdamond_names()
    return _damon_fs.update_schemes_stats(kdamond_names)

def update_schemes_tried_regions(kdamond_names=None):
    if kdamond_names == None:
        kdamond_names = running_kdamond_names()
    if _damon_fs == _damon_dbgfs:
        return 'DAMON debugfs doesn\'t support schemes tried regions'
    return _damon_fs.update_schemes_tried_regions(kdamond_names)

def update_schemes_status():
    names = running_kdamond_names()
    if len(names) == 0:
        return None
    err = update_schemes_stats(names)
    if err != None:
        return err
    return update_schemes_tried_regions(names)

def turn_damon_on(kdamonds_names):
    err = _damon_fs.turn_damon_on(kdamonds_names)
    if err:
        return err
    wait_current_kdamonds_turned_on()

def turn_damon_off(kdamonds_names):
    err = _damon_fs.turn_damon_off(kdamonds_names)
    if err:
        return err
    wait_current_kdamonds_turned_off()
