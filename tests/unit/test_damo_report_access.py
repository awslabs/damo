#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damo_records
import _damon
import damo_report_access

class TestDamoShow(unittest.TestCase):
    def test_sorted_access_pattern(self):
        record = _damo_records.DamonRecord.from_kvpairs(
            {
                "kdamond_idx": 0, "context_idx": 0,
                "intervals": {
                    "sample_us": "5ms", "aggr_us": "100ms",
                    "ops_update_us": "1s"
                    },
                "scheme_idx": 0, "target_id": None,
                "snapshots": [
                    {
                        "start_time": "0", "end_time": "1000000000",
                        "regions": [
                            {
                                "start": "4K", "end": "8K",
                                "nr_accesses": {
                                    "samples": 0, "percent": 0
                                    },
                                "age": {
                                    "usec": "1s", "aggr_intervals": 10
                                    }
                                },
                            {
                                "start": "8K", "end": "16K",
                                "nr_accesses": {
                                    "samples": 19, "percent": "95%"
                                    },
                                "age": {
                                    "usec": "100ms", "aggr_intervals": 1
                                    }
                                },
                            {
                                "start": "16K", "end": "22K",
                                "nr_accesses": {
                                    "samples": 10, "percent": 50
                                    },
                                "age": {
                                    "usec": "3s", "aggr_intervals": 30
                                    }
                                },

                            ],
                        "total_bytes": "3221225472"
                        }
                    ]
                })
        sorted_vals = damo_report_access.SortedAccessPatterns([record])
        self.assertEqual(sorted_vals.sz_regions[0], 4096)
        self.assertEqual(sorted_vals.sz_regions[-1], 8192)
        self.assertEqual(sorted_vals.access_rates_percent[0], 0)
        self.assertEqual(sorted_vals.access_rates_percent[-1], 95)
        self.assertEqual(sorted_vals.ages_us[0], 100000)
        self.assertEqual(sorted_vals.ages_us[-1], 3000000)

    def test_format_template(self):
        record = _damo_records.DamonRecord.from_kvpairs(
            {
                "kdamond_idx": 0, "context_idx": 0,
                "intervals": {
                    "sample_us": "5ms", "aggr_us": "100ms",
                    "ops_update_us": "1s"
                    },
                "scheme_idx": 0, "target_id": None,
                "snapshots": [
                    {
                        "start_time": "0", "end_time": "1000000000",
                        "regions": [
                            {
                                "start": "4K", "end": "8K",
                                "nr_accesses": {
                                    "samples": 0, "percent": 0
                                    },
                                "age": {
                                    "usec": "1s", "aggr_intervals": 10
                                    }
                                },
                            {
                                "start": "8K", "end": "16K",
                                "nr_accesses": {
                                    "samples": 19, "percent": "95%"
                                    },
                                "age": {
                                    "usec": "100ms", "aggr_intervals": 1
                                    }
                                },
                            {
                                "start": "16K", "end": "22K",
                                "nr_accesses": {
                                    "samples": 10, "percent": 50
                                    },
                                "age": {
                                    "usec": "3s", "aggr_intervals": 30
                                    }
                                },

                            ],
                        "total_bytes": "3221225472"
                        }
                    ]
                })
        self.assertEqual(damo_report_access.format_template(
            '<abs start time>', damo_report_access.record_formatters, [], None,
            None, None, record, False, None), '0 ns')

    def test_rescale(self):
        self.assertEqual(
                damo_report_access.rescale(10, [0, 100], [0, 10], False), 1)
        self.assertEqual(
                damo_report_access.rescale(10, [0, 100], [1, 11], False), 2)
        self.assertEqual(
                damo_report_access.rescale(20, [10, 110], [1, 11], False), 2)

if __name__ == '__main__':
    unittest.main()
