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

    def test_min_max_of_record(self):
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
        mm = damo_show.MinMaxOfRecords([record])
        self.assertEqual(mm.min_sz_region, 4096)
        self.assertEqual(mm.max_sz_region, 8192)
        self.assertEqual(mm.min_access_rate_percent, 0)
        self.assertEqual(mm.max_access_rate_percent, 95)
        self.assertEqual(mm.min_age_us, 100000)
        self.assertEqual(mm.max_age_us, 3000000)

if __name__ == '__main__':
    unittest.main()
