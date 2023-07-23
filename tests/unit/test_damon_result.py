#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damon_result

class TestDamon(unittest.TestCase):
    def test_parse_file_permission_str(self):
        perm, err = _damon_result.parse_file_permission_str('777')
        self.assertEqual(perm, 0o777)
        self.assertIsNone(err)

        perm, err = _damon_result.parse_file_permission_str('-123')
        self.assertIsNone(perm)
        self.assertIsNotNone(err)

        perm, err = _damon_result.parse_file_permission_str('1000')
        self.assertIsNone(perm)
        self.assertIsNotNone(err)

        perm, err = _damon_result.parse_file_permission_str('778')
        self.assertIsNone(perm)
        self.assertIsNotNone(err)

    def test_record_from_kvpairs(self):
        records = [_damon_result.DamonRecord.from_kvpairs(p) for p in [
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

if __name__ == '__main__':
    unittest.main()
