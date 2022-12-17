#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json
import os
import sys
import unittest

bindir = os.path.dirname(os.path.realpath(__file__))
damo_dir = os.path.join(bindir, '..', '..')
sys.path.append(damo_dir)

import _damon
import _damo_schemes_input

class TestDamoSchemesInput(unittest.TestCase):
    def test_damo_schemes_to_damos_without_filters(self):

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
human_readable_damos_kv_with_comments = '\n\n# some comments\n'.join(
        human_readable_damos_str.split('\n'))

        inputs = [base_damos_str, base_damos_str_with_comments,
                human_readable_damos_str,
                human_readable_damos_kv_with_comments]
        for txt in inputs:
            damos_list = _damo_schemes_input.damo_schemes_to_damos(txt)
            expected = _damon.Damos('0',
                        _damon.DamosAccessPattern(0, 0, 0, 0,
                            'sample_intervals', 0, 0, 'aggr_intervals'),
                        'stat',
                        _damon.DamosQuotas(0, 0, 0, 0, 0, 0),
                        _damon.DamosWatermarks('none', 0, 0, 0, 0), [], None, None)
            self.assertEqual(damos_list[0], expected)

    def test_damo_schemes_to_damos(self):
        inputs = [
                # no comment
                '''
                [
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
                        },
                        "filters": [
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
                    }
                ]
                ''',
                # with comments
                '''
                [
                    {
                        # some comment
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
                        },
                        "filters": [
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
                    }
                ]
                ''',
                # human redable
                '''
                [
                    {
                        # some comment
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
                        },
                        "filters": [
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
                    }
                ]
                ''',
        ]
        for txt in inputs:
            damos_list = _damo_schemes_input.damo_schemes_to_damos(txt)
            expected = _damon.Damos('0',
                        _damon.DamosAccessPattern(0, 0, 0, 0,
                            'sample_intervals', 0, 0, 'aggr_intervals'),
                        'stat',
                        _damon.DamosQuotas(0, 0, 0, 0, 0, 0),
                        _damon.DamosWatermarks('none', 0, 0, 0, 0),
                        [_damon.DamosFilter('0', 'anon', '', True),
                            _damon.DamosFilter('1', 'memcg',
                                '/all/latency-critical', False)], None, None)
            self.assertEqual(damos_list[0], expected)

if __name__ == '__main__':
    unittest.main()
