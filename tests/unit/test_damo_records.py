#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damo_records
import _damon

class TestDamon(unittest.TestCase):
    def test_parse_file_permission_str(self):
        perm, err = _damo_records.parse_file_permission_str('777')
        self.assertEqual(perm, 0o777)
        self.assertIsNone(err)

        perm, err = _damo_records.parse_file_permission_str('-123')
        self.assertIsNone(perm)
        self.assertIsNotNone(err)

        perm, err = _damo_records.parse_file_permission_str('1000')
        self.assertIsNone(perm)
        self.assertIsNotNone(err)

        perm, err = _damo_records.parse_file_permission_str('778')
        self.assertIsNone(perm)
        self.assertIsNotNone(err)

    def test_record_from_kvpairs(self):
        records = [_damo_records.DamonRecord.from_kvpairs(p) for p in [
            {
                "kdamond_idx": 0, "context_idx": 0,
                "intervals": {
                    "sample_us": "5ms", "aggr_us": "100ms",
                    "ops_update_us": "1s"
                    },
                "scheme_idx": 0, "target_id": None,
                "snapshots": [
                    {
                        "start_time": "1690134099856513792",
                        "end_time": "1690134099956513792",
                        "regions": [
                            {
                                "start": "4,294,967,296",
                                "end": "7,516,192,768",
                                "nr_accesses": {
                                    "samples": 0,
                                    "percent": None
                                    },
                                "age": {
                                    "usec": None,
                                    "aggr_intervals": "5,913"
                                    }
                                }
                            ],
                        "total_bytes": "3221225472"
                        }
                    ]
                }
            ]]
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0].snapshots), 1)

        # test DamonSnapshot.total_bytes added by commit 98c1bd8f467f6.  Test
        # older output that doesn't have the data.
        records = [_damo_records.DamonRecord.from_kvpairs(p) for p in [
            {
                "kdamond_idx": 0, "context_idx": 0,
                "intervals": {
                    "sample_us": "5ms", "aggr_us": "100ms",
                    "ops_update_us": "1s"
                    },
                "scheme_idx": 0, "target_id": None,
                "snapshots": [
                    {
                        "start_time": "1690134099856513792",
                        "end_time": "1690134099956513792",
                        "regions": [
                            {
                                "start": "4,294,967,296",
                                "end": "7,516,192,768",
                                "nr_accesses": {
                                    "samples": 0,
                                    "percent": None
                                    },
                                "age": {
                                    "usec": None,
                                    "aggr_intervals": "5,913"
                                    }
                                }
                            ],
                        }
                    ]
                }
            ]]
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0].snapshots), 1)

    def test_filter_by_address(self):
        ranges = [[3, 5], [6, 9], [10, 12]]
        region = _damon.DamonRegion(7, 8)
        self.assertEqual(
                _damo_records.filter_by_addr(_damon.DamonRegion(7, 8),
                    ranges), [_damon.DamonRegion(7, 8)])
        self.assertEqual(
                _damo_records.filter_by_addr(_damon.DamonRegion(1, 2),
                    ranges), [])
        self.assertEqual(
                _damo_records.filter_by_addr(_damon.DamonRegion(5, 6),
                    ranges), [])
        self.assertEqual(
                _damo_records.filter_by_addr(_damon.DamonRegion(1, 4),
                    ranges), [_damon.DamonRegion(3, 4)])
        self.assertEqual(
                _damo_records.filter_by_addr(_damon.DamonRegion(1, 20),
                    ranges), [_damon.DamonRegion(3, 5), _damon.DamonRegion(6,
                        9), _damon.DamonRegion(10, 12)])

    def test_parse_sort_bytes_ranges_input(self):
        self.assertEqual(
                _damo_records.parse_sort_bytes_ranges_input([['1G', '2G']]),
                ([[1024 * 1024 * 1024, 1024 * 1024 * 1024 * 2]], None))
        ranges, err = _damo_records.parse_sort_bytes_ranges_input(
                [['abc', 'def']])
        self.assertNotEqual(err, None)
        ranges, err = _damo_records.parse_sort_bytes_ranges_input([[4, 3]])
        self.assertNotEqual(err, None)
        ranges, err = _damo_records.parse_sort_bytes_ranges_input(
                [[5, 7], [2, 6]])
        self.assertEqual(err, 'overlapping range')

        self.assertEqual(
                _damo_records.parse_sort_bytes_ranges_input(
                    [[10, 20], [5, 7]]), ([[5, 7], [10, 20]], None))

if __name__ == '__main__':
    unittest.main()
