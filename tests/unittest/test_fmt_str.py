#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import os
import sys
import unittest

bindir = os.path.dirname(os.path.realpath(__file__))
damo_dir = os.path.join(bindir, '..', '..')
sys.path.append(damo_dir)

import _damo_fmt_str

class TestDamoFmtStr(unittest.TestCase):
    def test_format_nr(self):
        self.assertEqual(_damo_fmt_str.format_nr(123, False), '123')
        self.assertEqual(_damo_fmt_str.format_nr(1234, False), '1,234')
        self.assertEqual(_damo_fmt_str.format_nr(1234567, False), '1,234,567')

    def test_text_to_nr(self):
        self.assertEqual(_damo_fmt_str.text_to_nr('12'), 12)
        self.assertEqual(_damo_fmt_str.text_to_nr('1,234'), 1234)
        self.assertEqual(_damo_fmt_str.text_to_nr('1,234,567'), 1234567)

    def test_format_time(self):
        self.assertEqual(_damo_fmt_str.format_time_ns(123, False), '123 ns')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            123456, False), '123.456 us')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            123000, False), '123 us')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            123456789, False), '123.457 ms')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            123000000, False), '123 ms')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            123456789123, False), '2 m 3.457 s')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            123000000000, False), '2 m 3 s')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            60 * 1000 * 1000 * 1000, False), '1 m')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            60 * 1000 * 1000 * 1000 + 59 * 1000 * 1000 * 1000, False),
            '1 m 59 s')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            60 * 1000 * 1000 * 1000 + 59 * 1000 * 1000 * 1000 +
            123 * 1000 * 1000, False),
            '1 m 59.123 s')

if __name__ == '__main__':
    unittest.main()
