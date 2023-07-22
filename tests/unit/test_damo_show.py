#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damon
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

if __name__ == '__main__':
    unittest.main()
