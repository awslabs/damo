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

if __name__ == '__main__':
    unittest.main()
