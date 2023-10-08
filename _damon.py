# SPDX-License-Identifier: GPL-2.0

"""
Contains core functions for DAMON control.
"""

import collections
import copy
import os
import random
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

unit_percent = 'percent'
unit_samples = 'samples'
unit_usec = 'usec'
unit_aggr_intervals = 'aggr_intervals'

class DamonNrAccesses:
    samples = None
    percent = None

    def __init__(self, val, unit):
        if val == None or unit == None:
            return
        if unit == unit_samples:
            self.samples = _damo_fmt_str.text_to_nr(val)
        elif unit == unit_percent:
            self.percent = _damo_fmt_str.text_to_percent(val)
        else:
            raise Exception('invalid DamonNrAccesses unit \'%s\'' % unit)

    def __eq__(self, other):
        return (type(self) == type(other) and
                ((self.samples != None and self.samples == other.samples) or
                    (self.percent != None and self.percent == other.percent)))

    def add_unset_unit(self, intervals):
        if self.samples != None and self.percent != None:
            return
        max_val = intervals.aggr / intervals.sample
        if self.samples == None:
            self.samples = int(self.percent * max_val / 100)
        elif self.percent == None:
            self.percent = int(self.samples * 100.0 / max_val)

    def to_str(self, unit, raw):
        if unit == unit_percent:
            return '%s %%' % (_damo_fmt_str.format_nr(self.percent, raw))
        elif unit == unit_samples:
            return '%s %s' % (_damo_fmt_str.format_nr(self.samples, raw),
                    unit_samples)
        raise Exception('unsupported unit for NrAccesses (%s)' % unit)

    @classmethod
    def from_kvpairs(cls, kv):
        ret = DamonNrAccesses(None, None)
        if 'samples' in kv and kv['samples'] != None:
            ret.samples = _damo_fmt_str.text_to_nr(kv['samples'])
        if 'percent' in kv and kv['percent'] != None:
            ret.percent = _damo_fmt_str.text_to_percent(kv['percent'])
        return ret

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict(
                [('samples', self.samples), ('percent', self.percent)])

class DamonAge:
    usec = None
    aggr_intervals = None

    def __init__(self, val, unit):
        if val == None and unit != None:
            self.unit = unit
            return
        if val == None and unit == None:
            return
        if unit == unit_usec:
            self.usec = _damo_fmt_str.text_to_us(val)
        elif unit == unit_aggr_intervals:
            self.aggr_intervals = _damo_fmt_str.text_to_nr(val)
        else:
            raise Exception('DamonAge unsupported unit (%s)' % unit)

    def __eq__(self, other):
        return (type(self) == type(other) and
                ((self.usec != None and self.usec == other.usec) or
                    (self.aggr_intervals != None and
                        self.aggr_intervals == other.aggr_intervals)))

    def add_unset_unit(self, intervals):
        if self.usec != None and self.aggr_intervals != None:
            return
        if self.usec == None:
            self.usec = self.aggr_intervals * intervals.aggr
        elif self.aggr_intervals == None:
            self.aggr_intervals = int(self.usec / intervals.aggr)

    def to_str(self, unit, raw):
        if unit == unit_usec:
            return _damo_fmt_str.format_time_us_exact(self.usec, raw)
        return '%s %s' % (_damo_fmt_str.format_nr(self.aggr_intervals, raw),
                unit_aggr_intervals)

    @classmethod
    def from_kvpairs(cls, kv):
        ret = DamonAge(None, None)
        if kv['usec'] != None:
            ret.usec = _damo_fmt_str.text_to_us(kv['usec'])
        if kv['aggr_intervals'] != None:
            ret.aggr_intervals = _damo_fmt_str.text_to_nr(kv['aggr_intervals'])
        return ret

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict(
                [('usec', _damo_fmt_str.format_time_us_exact(self.usec, raw)
                    if self.usec != None else None),
                    ('aggr_intervals',
                        _damo_fmt_str.format_nr(self.aggr_intervals, raw)
                        if self.aggr_intervals != None else None)])

class DamonRegion:
    # [start, end)
    start = None
    end = None
    # nr_accesses and age could be None
    nr_accesses = None
    age = None

    def __init__(self, start, end, nr_accesses=None, nr_accesses_unit=None,
            age=None, age_unit=None):
        self.start = _damo_fmt_str.text_to_bytes(start)
        self.end = _damo_fmt_str.text_to_bytes(end)

        if nr_accesses == None:
            return
        self.nr_accesses = DamonNrAccesses(nr_accesses, nr_accesses_unit)
        self.age = DamonAge(age, age_unit)

    def to_str(self, raw, intervals=None):
        if self.nr_accesses == None:
            return _damo_fmt_str.format_addr_range(self.start, self.end, raw)

        if intervals != None:
            self.nr_accesses.add_unset_unit(intervals)
            self.age.add_unset_unit(intervals)

        if raw == False and intervals != None:
            nr_accesses_unit = unit_percent
            age_unit = unit_usec
        else:
            nr_accesses_unit = unit_samples
            age_unit = unit_aggr_intervals
        return '%s: nr_accesses: %s, age: %s' % (
                _damo_fmt_str.format_addr_range(self.start, self.end, raw),
                self.nr_accesses.to_str(nr_accesses_unit, raw),
                self.age.to_str(age_unit, raw))

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        if self.nr_accesses == None:
            return type(self) == type(other) and '%s' % self == '%s' % other

    # For aggregate_snapshots() support
    def __hash__(self):
        identification = '%s-%s' % (self.start, self.end)
        return hash(identification)

    @classmethod
    def from_kvpairs(cls, kvpairs):
        if not 'nr_accesses' in kvpairs:
            return DamonRegion(kvpairs['start'], kvpairs['end'])
        region = DamonRegion(kvpairs['start'], kvpairs['end'])
        region.nr_accesses = DamonNrAccesses.from_kvpairs(
                kvpairs['nr_accesses'])
        region.age = DamonAge.from_kvpairs(kvpairs['age'])
        return region

    def to_kvpairs(self, raw=False):
        if self.nr_accesses == None:
            return collections.OrderedDict([
                ('start', _damo_fmt_str.format_nr(self.start, raw)),
                ('end', _damo_fmt_str.format_nr(self.end, raw))])
        return collections.OrderedDict([
            ('start', _damo_fmt_str.format_nr(self.start, raw)),
            ('end', _damo_fmt_str.format_nr(self.end, raw)),
            ('nr_accesses', self.nr_accesses.to_kvpairs(raw)),
            ('age', self.age.to_kvpairs(raw))])

    def size(self):
        return self.end - self.start

class DamonTarget:
    pid = None
    regions = None

    def __init__(self, pid, regions):
        self.pid = pid
        self.regions = regions

    def to_str(self, raw):
        lines = ['pid: %s' % self.pid]
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
        return DamonTarget(kvpairs['pid'], regions)

    def to_kvpairs(self, raw=False):
        kvp = collections.OrderedDict()
        kvp['pid'] = self.pid
        kvp['regions'] = [r.to_kvpairs(raw) for r in self.regions]
        return kvp

class DamosAccessPattern:
    sz_bytes = None
    nr_acc_min_max = None # [min/max DamonNrAccesses]
    nr_accesses_unit = None
    age_min_max = None # [min/max DamonAge]
    age_unit = None

    # every region by default, so that it can be used for monitoring
    def __init__(self, sz_bytes=['min', 'max'],
            nr_accesses=['min', 'max'], nr_accesses_unit=unit_percent,
            age=['min', 'max'], age_unit=unit_usec):
        self.sz_bytes = [_damo_fmt_str.text_to_bytes(sz_bytes[0]),
                _damo_fmt_str.text_to_bytes(sz_bytes[1])]

        self.nr_acc_min_max = [
                DamonNrAccesses(nr_accesses[0], nr_accesses_unit),
                DamonNrAccesses(nr_accesses[1], nr_accesses_unit)]
        self.nr_accesses_unit = nr_accesses_unit
        self.age_min_max = [
                DamonAge(age[0], age_unit), DamonAge(age[1], age_unit)]
        self.age_unit = age_unit

    def to_str(self, raw):
        lines = [
            'sz: [%s, %s]' % (_damo_fmt_str.format_sz(self.sz_bytes[0], raw),
                _damo_fmt_str.format_sz(self.sz_bytes[1], raw)),
            ]
        lines.append('nr_accesses: [%s, %s]' % (
            self.nr_acc_min_max[0].to_str(self.nr_accesses_unit, raw),
            self.nr_acc_min_max[1].to_str(self.nr_accesses_unit, raw)))
        lines.append('age: [%s, %s]' % (
            self.age_min_max[0].to_str(self.age_unit, raw),
            self.age_min_max[1].to_str(self.age_unit, raw)))
        return '\n'.join(lines)

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.sz_bytes == other.sz_bytes and
                self.nr_acc_min_max == other.nr_acc_min_max and
                self.age_min_max == other.age_min_max)

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
        min_nr_accesses = self.nr_acc_min_max[0].to_str(
                self.nr_accesses_unit, raw)
        max_nr_accesses = self.nr_acc_min_max[1].to_str(
                self.nr_accesses_unit, raw)
        min_age = self.age_min_max[0].to_str(self.age_unit, raw)
        max_age = self.age_min_max[1].to_str(self.age_unit, raw)

        return collections.OrderedDict([
            ('sz_bytes', (collections.OrderedDict([
                ('min', _damo_fmt_str.format_sz(self.sz_bytes[0], raw)),
                ('max', _damo_fmt_str.format_sz(self.sz_bytes[1], raw))]))),
            ('nr_accesses', (collections.OrderedDict([
                ('min', min_nr_accesses), ('max', max_nr_accesses)]))),
            ('age', (collections.OrderedDict([
                ('min', min_age), ('max', max_age)]))),
            ])

    def convert_for_units(self, nr_accesses_unit, age_unit, intervals):
        self.nr_acc_min_max[0].add_unset_unit(intervals)
        self.nr_acc_min_max[1].add_unset_unit(intervals)
        self.age_min_max[0].add_unset_unit(intervals)
        self.age_min_max[1].add_unset_unit(intervals)
        self.nr_accesses_unit = nr_accesses_unit
        self.age_unit = age_unit

    def converted_for_units(self, nr_accesses_unit, age_unit, intervals):
        copied = copy.deepcopy(self)
        copied.convert_for_units(nr_accesses_unit, age_unit, intervals)
        return copied

    def effectively_equal(self, other, intervals):
        return (
                self.converted_for_units(
                    unit_samples, unit_aggr_intervals, intervals) ==
                other.converted_for_units(
                    unit_samples, unit_aggr_intervals, intervals))

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
                _damo_fmt_str.format_time_ns(self.time_ms * 1000000, raw),
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
        if not metric in [damos_wmarks_metric_none,
                damos_wmarks_metric_free_mem_rate]:
            raise Exception('wrong watermark metric (%s)' % metric)
        self.metric = metric
        self.interval_us = _damo_fmt_str.text_to_us(interval_us)
        self.high_permil = _damo_fmt_str.text_to_permil(high)
        self.mid_permil = _damo_fmt_str.text_to_permil(mid)
        self.low_permil = _damo_fmt_str.text_to_permil(low)

    def to_str(self, raw):
        return '\n'.join([
            'metric %s, interval %s' % (self.metric,
                _damo_fmt_str.format_time_us(self.interval_us, raw)),
            '%s, %s, %s' % (
                _damo_fmt_str.format_permil(self.high_permil, raw),
                _damo_fmt_str.format_permil(self.mid_permil, raw),
                _damo_fmt_str.format_permil(self.low_permil, raw)),
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
    filter_type = None  # anon, memcg, addr, or target
    matching = None
    memcg_path = None
    address_range = None    # DamonRegion
    damon_target_idx = None

    def __init__(self, filter_type, matching, memcg_path=None,
            address_range=None, damon_target_idx=None):
        self.filter_type = filter_type
        self.matching = _damo_fmt_str.text_to_bool(matching)
        self.memcg_path = memcg_path
        self.address_range = address_range
        if damon_target_idx != None:
            self.damon_target_idx = _damo_fmt_str.text_to_nr(damon_target_idx)

    def to_str(self, raw):
        txt = '%s %s' % (self.filter_type,
                'matching' if self.matching else 'nomatching')
        if self.filter_type == 'anon':
            return txt
        if self.filter_type == 'memcg':
            return '%s %s' % (txt, self.memcg_path)
        if self.filter_type == 'addr':
            return '%s %s' % (txt, self.address_range.to_str(raw))
        if self.filter_type == 'target':
            return '%s %s' % (txt, _damo_fmt_str.format_nr(
                    self.damon_target_idx, raw))

    def __str__(self):
        return self.to_str(False)

    def __eq__(self, other):
        return type(self) == type(other) and '%s' % self == '%s' % other

    @classmethod
    def from_kvpairs(cls, kv):
        return DamosFilter(kv['filter_type'], kv['matching'],
                kv['memcg_path'] if kv['filter_type'] == 'memcg' else '',
                DamonRegion.from_kvpairs(kv['address_range'])
                    if kv['filter_type'] == 'addr' else None,
                kv['damon_target_idx']
                    if kv['filter_type'] == 'target' else None)

    def to_kvpairs(self, raw=False):
        return collections.OrderedDict([
            ('filter_type', self.filter_type),
            ('matching', self.matching),
            ('memcg_path', self.memcg_path),
            ('address_range', self.address_range.to_kvpairs(raw) if
                self.address_range != None else None),
            ('damon_target_idx',
                _damo_fmt_str.format_nr(self.damon_target_idx, raw)
                if self.damon_target_idx != None else None)])

class DamosStats:
    nr_tried = None
    sz_tried = None
    nr_applied = None
    sz_applied = None
    qt_exceeds = None

    def __init__(self, nr_tried=0, sz_tried=0, nr_applied=0, sz_applied=0,
            qt_exceeds=0):
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

    def to_kvpairs(self, raw=False):
        kv = collections.OrderedDict()
        kv['nr_tried'] = _damo_fmt_str.format_nr(self.nr_tried, raw)
        kv['sz_tried'] = _damo_fmt_str.format_sz(self.sz_tried, raw)
        kv['nr_applied'] = _damo_fmt_str.format_nr(self.nr_applied, raw)
        kv['sz_applied'] = _damo_fmt_str.format_sz(self.sz_applied, raw)
        kv['qt_exceeds'] = _damo_fmt_str.format_nr(self.qt_exceeds, raw)
        return kv

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
    access_pattern = None
    action = None
    apply_interval_us = None
    quotas = None
    watermarks = None
    filters = None
    stats = None
    tried_regions = None
    tried_bytes = None

    # for monitoring only by default
    def __init__(self, access_pattern=None, action=damos_action_stat,
            apply_interval_us=None,
            quotas=None, watermarks=None, filters=None, stats=None,
            tried_regions=None, tried_bytes=None):
        self.access_pattern = (access_pattern
                if access_pattern != None else DamosAccessPattern())
        if not action in damos_actions:
            raise Exception('wrong damos action: %s' % action)
        self.action = action
        if apply_interval_us != None:
            self.apply_interval_us = _damo_fmt_str.text_to_us(
                    apply_interval_us)
        else:
            self.apply_interval_us = 0
        self.quotas = quotas if quotas != None else DamosQuotas()
        self.watermarks = (watermarks
                if watermarks != None else DamosWatermarks())
        self.filters = filters if filters != None else []
        self.stats = stats if stats != None else DamosStats()
        self.tried_regions = tried_regions
        if self.tried_regions == None:
            self.tried_regions = []
        self.tried_bytes = 0
        if tried_bytes:
            self.tried_bytes = _damo_fmt_str.text_to_bytes(
                    tried_bytes)
        else:
            for region in self.tried_regions:
                self.tried_bytes += region.size()

    def to_str(self, raw):
        lines = ['action: %s per %s' % (self.action,
            _damo_fmt_str.format_time_us(self.apply_interval_us, raw)
            if self.apply_interval_us != 0 else 'aggr interval')]
        lines.append('target access pattern')
        lines.append(_damo_fmt_str.indent_lines(
            self.access_pattern.to_str(raw), 4))
        lines.append('quotas')
        lines.append(_damo_fmt_str.indent_lines(self.quotas.to_str(raw), 4))
        lines.append('watermarks')
        lines.append(_damo_fmt_str.indent_lines(
            self.watermarks.to_str(raw), 4))
        for idx, damos_filter in enumerate(self.filters):
            lines.append('filter %d' % idx)
            lines.append(_damo_fmt_str.indent_lines(
                damos_filter.to_str(raw), 4))
        if self.stats != None:
            lines.append('statistics')
            lines.append(_damo_fmt_str.indent_lines(self.stats.to_str(raw), 4))
        if self.tried_regions != None:
            lines.append('tried regions (%s)' % _damo_fmt_str.format_sz(
                    self.tried_bytes, raw))
            for region in self.tried_regions:
                lines.append(_damo_fmt_str.indent_lines(region.to_str(raw), 4))
        return '\n'.join(lines)

    def __str__(self):
        return self.to_str(False)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        return (type(self) == type(other) and
                self.access_pattern == other.access_pattern and
                self.action == other.action and
                self.apply_interval_us == other.apply_interval_us and
                self.quotas == other.quotas and
                self.watermarks == other.watermarks and
                self.filters == other.filters)

    @classmethod
    def from_kvpairs(cls, kv):
        filters = []
        if 'filters' in kv:
            for damos_filter_kv in kv['filters']:
                filters.append(DamosFilter.from_kvpairs(damos_filter_kv))
        return Damos(DamosAccessPattern.from_kvpairs(kv['access_pattern'])
                    if 'access_pattern' in kv else DamosAccessPattern(),
                kv['action'] if 'action' in kv else damos_action_stat,
                kv['apply_interval_us'] if 'apply_interval_us' in kv else None,
                DamosQuotas.from_kvpairs(kv['quotas'])
                    if 'quotas' in kv else DamosQuotas(),
                DamosWatermarks.from_kvpairs(kv['watermarks'])
                    if 'watermarks' in kv else DamosWatermarks(),
                filters,
                None, None)

    def to_kvpairs(self, raw=False):
        kv = collections.OrderedDict()
        kv['action'] = self.action
        kv['access_pattern'] = self.access_pattern.to_kvpairs(raw)
        kv['apply_interval_us'] = self.apply_interval_us
        kv['quotas'] = self.quotas.to_kvpairs(raw)
        kv['watermarks'] = self.watermarks.to_kvpairs(raw)
        filters = []
        for damos_filter in self.filters:
            filters.append(damos_filter.to_kvpairs(raw))
        kv['filters'] = filters
        kv['stats'] = self.stats.to_kvpairs(raw)
        return kv

    def effectively_equal(self, other, intervals):
        return (type(self) == type(other) and
                self.access_pattern.effectively_equal(
                    other.access_pattern, intervals) and
                self.action == other.action and
                self.apply_interval_us == other.apply_interval_us and
                self.quotas == other.quotas and
                self.watermarks == other.watermarks and
                self.filters == other.filters)

class DamonCtx:
    ops = None
    targets = None
    intervals = None
    nr_regions = None
    schemes = None

    def __init__(self, ops, targets, intervals, nr_regions, schemes):
        self.ops = ops
        self.targets = targets
        self.intervals = intervals
        self.nr_regions = nr_regions
        self.schemes = schemes

    def to_str(self, raw):
        lines = ['ops: %s' % self.ops]
        for idx, target in enumerate(self.targets):
            lines.append('target %d' % idx)
            lines.append(_damo_fmt_str.indent_lines(target.to_str(raw), 4))
        lines.append('intervals: %s' % self.intervals.to_str(raw))
        lines.append('nr_regions: %s' % self.nr_regions.to_str(raw))
        for idx, scheme in enumerate(self.schemes):
            lines.append('scheme %d' % idx)
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
        ctx = DamonCtx(
                kv['ops'],
                [DamonTarget.from_kvpairs(t) for t in kv['targets']],
                DamonIntervals.from_kvpairs(kv['intervals'])
                    if 'intervals' in kv else DamonIntervals(),
                DamonNrRegionsRange.from_kvpairs(kv['nr_regions'])
                    if 'nr_regions' in kv else DAmonNrRegionsRange(),
                [Damos.from_kvpairs(s) for s in kv['schemes']]
                    if 'schemes' in kv else [])
        return ctx

    def to_kvpairs(self, raw=False):
        kv = collections.OrderedDict({})
        kv['ops'] = self.ops
        kv['targets'] = [t.to_kvpairs(raw) for t in self.targets]
        kv['intervals'] = self.intervals.to_kvpairs(raw)
        kv['nr_regions'] = self.nr_regions.to_kvpairs(raw)
        kv['schemes'] = [s.to_kvpairs(raw) for s in self.schemes]
        return kv

def target_has_pid(ops):
    return ops in ['vaddr', 'fvaddr']

class Kdamond:
    state = None
    pid = None
    contexts = None

    def __init__(self, state, pid, contexts):
        self.state = state
        self.pid = pid
        self.contexts = contexts

    def summary_str(self):
        return 'state: %s, pid: %s' % (self.state, self.pid)

    def to_str(self, raw):
        lines = [self.summary_str()]
        for idx, ctx in enumerate(self.contexts):
            lines.append('context %d' % idx)
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
        return Kdamond(
                kv['state'] if 'state' in kv else 'off',
                kv['pid'] if 'pid' in kv else None,
                [DamonCtx.from_kvpairs(c) for c in kv['contexts']])

    def to_kvpairs(self, raw=False):
        kv = collections.OrderedDict()
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
            'schemes_filters',          # merged in v6.3-rc1
            'schemes_tried_regions_sz', # merged in v6.6-rc1
            'schemes_apply_interval',   # merged in v6.6-rc4 based mm tree
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

# DAMON control

def stage_kdamonds(kdamonds):
    return _damon_fs.stage_kdamonds(kdamonds)

def commit_staged(kdamond_idxs):
    if _damon_fs == _damon_dbgfs:
        return 'debugfs interface does not support commit_staged()'
    return _damon_fs.commit_staged(kdamond_idxs)

def commit(kdamonds):
    err = stage_kdamonds(kdamonds)
    if err:
        return 'staging updates failed (%s)' % err
    err = commit_staged(['%s' % idx for idx, k in enumerate(kdamonds)])
    if err:
        return 'commit staged updates filed (%s)' % err
    return None

def update_schemes_stats(kdamond_idxs=None):
    if kdamond_idxs == None:
        kdamond_idxs = running_kdamond_idxs()
    return _damon_fs.update_schemes_stats(kdamond_idxs)

def update_schemes_tried_bytes(kdamond_idxs=None):
    if kdamond_idxs == None:
        kdamond_idxs = running_kdamond_idxs()
    return _damon_fs.update_schemes_tried_bytes(kdamond_idxs)

def update_schemes_tried_regions(kdamond_idxs=None):
    if kdamond_idxs == None:
        kdamond_idxs = running_kdamond_idxs()
    return _damon_fs.update_schemes_tried_regions(kdamond_idxs)

def update_schemes_status(stats=True, tried_regions=True):
    '''Returns error string or None'''
    idxs = running_kdamond_idxs()
    if len(idxs) == 0:
        return None
    if stats:
        err = update_schemes_stats(idxs)
        if err != None:
            return err
    if tried_regions and feature_supported('schemes_tried_regions'):
        return update_schemes_tried_regions(idxs)
    return None

def turn_damon_on(kdamonds_idxs):
    err = _damon_fs.turn_damon_on(kdamonds_idxs)
    if err:
        return err
    wait_kdamonds_turned_on()

def turn_damon_off(kdamonds_idxs):
    err = _damon_fs.turn_damon_off(kdamonds_idxs)
    if err:
        return err
    wait_kdamonds_turned_off()

# DAMON status reading

def is_kdamond_running(kdamond_idx):
    return _damon_fs.is_kdamond_running(kdamond_idx)

def current_kdamonds():
    return _damon_fs.current_kdamonds()

def update_read_kdamonds(nr_retries=0):
    err = 'assumed error'
    nr_tries = 0
    while True:
        err = update_schemes_status()
        nr_tries += 1
        if err == None or nr_tries > nr_retries:
            break
        time.sleep(random.randrange(2**(nr_tries - 1), 2**nr_tries) / 100)
    if err:
        return None, err
    return current_kdamonds(), None

def nr_kdamonds():
    return _damon_fs.nr_kdamonds()

def running_kdamond_idxs():
    return [idx for idx in range(nr_kdamonds())
            if is_kdamond_running(idx)]

def any_kdamond_running():
    for idx in range(nr_kdamonds()):
        if is_kdamond_running(idx):
            return True
    return False

def wait_kdamonds_turned_on():
    for idx in range(nr_kdamonds()):
        while not is_kdamond_running(idx):
            time.sleep(1)

def wait_kdamonds_turned_off():
    for idx in range(nr_kdamonds()):
        while is_kdamond_running(idx):
            time.sleep(1)
