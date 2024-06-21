#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import copy
import json
import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damo_deprecated
import _damon
import _damon_args

class TestDamoSchemesInput(unittest.TestCase):
    def test_schemes_option_to_damos(self):
        base_damos_kv = [
                {
                    "comments": "just for testing",
                    "action": "stat",
                    "access_pattern": {
                        "sz_bytes": {"min": 0, "max": 0},
                        "nr_accesses": {
                            "min": "0 samples",
                            "max": "0 samples"},
                        "age": {
                            "min": "0 aggr_intervals",
                            "max": "0 aggr_intervals"},
                        },
                    "quotas": {
                        "time_ms": 0,
                        "sz_bytes": 0,
                        "reset_interval_ms": 0,
                        "weights": {
                            "sz_permil": 0,
                            "nr_accesses_permil": 0,
                            "age_permil": 0},
                        },
                    "watermarks": {
                        "metric": "none",
                        "interval_us": 0,
                        "high_permil": 0,
                        "mid_permil": 0,
                        "low_permil": 0
                        }
                    }
                ]
        human_readable_damos_kv = [
                {
                    "action": "stat",
                    "access_pattern": {
                        "sz_bytes": {"min": "min", "max": "min"},
                        "nr_accesses": {
                            "min": "0 samples",
                            "max": "0 samples"},
                        "age": {
                            "min": "0 aggr_intervals",
                            "max": "0 aggr_intervals"},
                        },
                    "quotas": {
                        "time_ms": "0s",
                        "sz_bytes": "0B",
                        "reset_interval_ms": "0us",
                        "weights": {
                            "sz_permil": 0,
                            "nr_accesses_permil": 0,
                            "age_permil": 0},
                        },
                    "watermarks": {
                        "metric": "none",
                        "interval_us": "0us",
                        "high_permil": 0,
                        "mid_permil": 0,
                        "low_permil": 0
                        }
                    }
                ]
        base_filters_kv = [
                {
                    "filter_type": "anon",
                    "memcg_path": "",
                    "matching": "yes",
                    },
                {
                    "filter_type": "memcg",
                    "memcg_path": "/all/latency-critical",
                    "matching": False,
                    }
                ]

        base_damos_kv_with_filters = copy.deepcopy(base_damos_kv)
        base_damos_kv_with_filters[0]['filters'] = base_filters_kv

        base_damos_str = json.dumps(base_damos_kv, indent=4)
        human_readable_damos_str = json.dumps(human_readable_damos_kv,
                indent=4)

        human_readable_damos_kv_with_filters = copy.deepcopy(
                human_readable_damos_kv)
        human_readable_damos_kv_with_filters[0]['filters'] = base_filters_kv

        base_damos_with_filters_str = json.dumps(base_damos_kv_with_filters,
                indent=4)
        human_readable_damos_with_filters_str = json.dumps(
                human_readable_damos_kv_with_filters, indent=4)

        expected_damos_wo_filters = [_damon.Damos(
                _damon.DamosAccessPattern([0, 0],
                    [0, 0], _damon.unit_samples,
                    [0, 0], _damon.unit_aggr_intervals),
                'stat', None,
                None,
                _damon.DamosQuotas(0, 0, 0, [0, 0, 0]),
                _damon.DamosWatermarks('none', 0, 0, 0, 0), [], None,
                None)]
        expected_damos_w_filters = [_damon.Damos(
                _damon.DamosAccessPattern([0, 0],
                    [0, 0], _damon.unit_samples,
                    [0, 0], _damon.unit_aggr_intervals),
                'stat', None,
                None,
                _damon.DamosQuotas(0, 0, 0, [0, 0, 0]),
                _damon.DamosWatermarks('none', 0, 0, 0, 0),
                [_damon.DamosFilter('anon', True, ''),
                    _damon.DamosFilter('memcg', False,
                        '/all/latency-critical')], None, None)]

        def get_damos_from_damo_schemes(damo_schemes):
            damos, err = _damon_args.schemes_option_to_damos(
                    damo_schemes)
            return damos

        _test_damo_common.test_input_expects(self,
                get_damos_from_damo_schemes,
                {
                    base_damos_str: expected_damos_wo_filters,
                    human_readable_damos_str: expected_damos_wo_filters,
                    base_damos_with_filters_str: expected_damos_w_filters,
                    human_readable_damos_with_filters_str:
                    expected_damos_w_filters})

    def test_conversion_from_singleline_to_json(self):
        _damo_deprecated.avoid_crashing_single_line_scheme_for_testing = True
        damos_list, err = _damo_deprecated.damo_single_line_schemes_to_damos(
'''
min max     5 max       min max     hugepage
2M max      min min     7s max      nohugepage''')
        self.assertEqual(err, None)
        self.assertEqual(damos_list,
                [
                    _damon.Damos(
                        access_pattern=_damon.DamosAccessPattern(
                            sz_bytes=['min', 'max'],
                            nr_accesses=['5', 'max'],
                            nr_accesses_unit=_damon.unit_percent,
                            age=['min', 'max'], age_unit=_damon.unit_usec),
                        action=_damon.damos_action_hugepage),
                    _damon.Damos(
                        access_pattern=_damon.DamosAccessPattern(
                            sz_bytes=['2M', 'max'],
                            nr_accesses=['min', 'min'],
                            nr_accesses_unit=_damon.unit_percent,
                            age=['7s', 'max'], age_unit=_damon.unit_usec),
                        action=_damon.damos_action_nohugepage)])

if __name__ == '__main__':
    unittest.main()
