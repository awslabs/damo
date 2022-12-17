#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

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
import _damo_schemes_input

class TestDamoSchemesInput(unittest.TestCase):
    def test_damo_schemes_to_damos(self):
        base_damos_kv = [
                {
                    "name": "0",
                    "action": "stat",
                    "access_pattern": {
                        "min_sz_bytes": 0,
                        "max_sz_bytes": 0,
                        "min_nr_accesses": "0 sample_intervals",
                        "max_nr_accesses": "0 sample_intervals",
                        "min_age": "0 aggr_intervals",
                        "max_age": "0 aggr_intervals"
                        },
                    "quotas": {
                        "time_ms": 0,
                        "sz_bytes": 0,
                        "reset_interval_ms": 0,
                        "weight_sz_permil": 0,
                        "weight_nr_accesses_permil": 0,
                        "weight_age_permil": 0
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
                    "name": "0",
                    "action": "stat",
                    "access_pattern": {
                        "min_sz_bytes": "min",
                        "max_sz_bytes": "min",
                        "min_nr_accesses": "0 sample_intervals",
                        "max_nr_accesses": "0 sample_intervals",
                        "min_age": "0 aggr_intervals",
                        "max_age": "0 aggr_intervals"
                        },
                    "quotas": {
                        "time_ms": "0s",
                        "sz_bytes": "0B",
                        "reset_interval_ms": "0us",
                        "weight_sz_permil": 0,
                        "weight_nr_accesses_permil": 0,
                        "weight_age_permil": 0
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
        base_damos_str = json.dumps(base_damos_kv, indent=4)
        base_damos_str_with_comments = '\n\n# some comments\n'.join(
                base_damos_str.split('\n'))
        human_readable_damos_str = json.dumps(human_readable_damos_kv, indent=4)
        human_readable_damos_str_with_comments = '\n\n# some comments\n'.join(
                human_readable_damos_str.split('\n'))

        base_damos_kv_with_filters = copy.deepcopy(base_damos_kv)
        base_filters_kv = [
                {
                    "name": "0",
                    "filter_type": "anon",
                    "memcg_path": "",
                    "matching": "true"
                    },
                {
                    "name": "1",
                    "filter_type": "memcg",
                    "memcg_path": "/all/latency-critical",
                    "matching": "false"
                    }
                ]
        base_damos_kv_with_filters[0]['filters'] = base_filters_kv
        human_readable_damos_kv_with_filters = copy.deepcopy(
                human_readable_damos_kv)
        human_readable_damos_kv_with_filters[0]['filters'] = base_filters_kv

        base_damos_with_filters_str = json.dumps(base_damos_kv_with_filters,
                indent=4)
        base_damos_with_filters_str_with_comments = (
                '\n\n# some comments\n'.join(
                    base_damos_with_filters_str.split('\n')))
        human_readable_damos_with_filters_str = json.dumps(
                human_readable_damos_kv_with_filters, indent=4)
        human_readable_damos_with_filters_str_with_comments = (
                '\n\n# some comments\n'.join(
                    human_readable_damos_with_filters_str.split('\n')))

        expected_damos_wo_filters = [_damon.Damos('0',
                _damon.DamosAccessPattern(0, 0, 0, 0,
                    'sample_intervals', 0, 0, 'aggr_intervals'),
                'stat',
                _damon.DamosQuotas(0, 0, 0, 0, 0, 0),
                _damon.DamosWatermarks('none', 0, 0, 0, 0), [], None, None)]
        expected_damos_w_filters = [_damon.Damos('0',
                _damon.DamosAccessPattern(0, 0, 0, 0,
                    'sample_intervals', 0, 0, 'aggr_intervals'),
                'stat',
                _damon.DamosQuotas(0, 0, 0, 0, 0, 0),
                _damon.DamosWatermarks('none', 0, 0, 0, 0),
                [_damon.DamosFilter('0', 'anon', '', True),
                    _damon.DamosFilter('1', 'memcg',
                        '/all/latency-critical', False)], None, None)]

        inputs_expects = {
                base_damos_str: expected_damos_wo_filters,
                base_damos_str_with_comments: expected_damos_wo_filters,
                human_readable_damos_str: expected_damos_wo_filters,
                human_readable_damos_str_with_comments:
                expected_damos_wo_filters,
                base_damos_with_filters_str: expected_damos_w_filters,
                base_damos_with_filters_str_with_comments:
                expected_damos_w_filters,
                human_readable_damos_with_filters_str:
                expected_damos_w_filters,
                human_readable_damos_with_filters_str_with_comments:
                expected_damos_w_filters}

        _test_damo_common.test_input_expects(self,
                _damo_schemes_input.damo_schemes_to_damos,
                inputs_expects)

if __name__ == '__main__':
    unittest.main()
