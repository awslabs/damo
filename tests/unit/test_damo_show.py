#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damon
import _damon_result
import damo_show

class TestDamoShow(unittest.TestCase):
    def test_filter_by_address(self):
        ranges = [[3, 5], [6, 9], [10, 12]]
        region = _damon.DamonRegion(7, 8)
        self.assertEqual(
                damo_show.filter_by_addr(_damon.DamonRegion(7, 8), ranges),
                [_damon.DamonRegion(7, 8)])
        self.assertEqual(
                damo_show.filter_by_addr(_damon.DamonRegion(1, 2), ranges),
                [])
        self.assertEqual(
                damo_show.filter_by_addr(_damon.DamonRegion(5, 6), ranges),
                [])
        self.assertEqual(
                damo_show.filter_by_addr(_damon.DamonRegion(1, 4), ranges),
                [_damon.DamonRegion(3, 4)])
        self.assertEqual(
                damo_show.filter_by_addr(_damon.DamonRegion(1, 20), ranges),
                [_damon.DamonRegion(3, 5), _damon.DamonRegion(6, 9),
                    _damon.DamonRegion(10, 12)])

    def test_convert_addr_ranges_input(self):
        self.assertEqual(
                damo_show.convert_addr_ranges_input([['1G', '2G']]),
                ([[1024 * 1024 * 1024, 1024 * 1024 * 1024 * 2]], None))
        ranges, err = damo_show.convert_addr_ranges_input([['abc', 'def']])
        self.assertNotEqual(err, None)
        ranges, err = damo_show.convert_addr_ranges_input([[4, 3]])
        self.assertNotEqual(err, None)
        ranges, err = damo_show.convert_addr_ranges_input([[5, 7], [2, 6]])
        self.assertEqual(err, 'overlapping range')

        self.assertEqual(
                damo_show.convert_addr_ranges_input([[10, 20], [5, 7]]),
                ([[5, 7], [10, 20]], None))

    def test_sorted_access_pattern(self):
        record = _damon_result.DamonRecord.from_kvpairs(
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
        sorted_vals = damo_show.SortedAccessPatterns([record])
        self.assertEqual(sorted_vals.sz_regions[0], 4096)
        self.assertEqual(sorted_vals.sz_regions[-1], 8192)
        self.assertEqual(sorted_vals.access_rates_percent[0], 0)
        self.assertEqual(sorted_vals.access_rates_percent[-1], 95)
        self.assertEqual(sorted_vals.ages_us[0], 100000)
        self.assertEqual(sorted_vals.ages_us[-1], 3000000)

    def test_format_template(self):
        record = _damon_result.DamonRecord.from_kvpairs(
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
        self.assertEqual(damo_show.format_template('<abs start time>',
            damo_show.record_formatters, [], None, None, None, record, False,
            None), '0 ns')

    def test_rescale(self):
        self.assertEqual(damo_show.rescale(10, [0, 100], [0, 10], False), 1)
        self.assertEqual(
                damo_show.rescale(10, [0, 100], [1, 11], False), 2)
        self.assertEqual(
                damo_show.rescale(20, [10, 110], [1, 11], False), 2)

if __name__ == '__main__':
    unittest.main()
