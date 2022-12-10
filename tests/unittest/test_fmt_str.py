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
            123456, False), '123 us 456 ns')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            123000, False), '123 us')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            123456789, False), '123 ms 456 us 789 ns')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            123000000, False), '123 ms')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            123456789123, False), '2 m 3 s 456 ms 789 us 123 ns')
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
            '1 m 59 s 123 ms')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            2 * 60 * 60 * 1000 * 1000 * 1000 +
            60 * 1000 * 1000 * 1000 + 59 * 1000 * 1000 * 1000 +
            123 * 1000 * 1000, False),
            '2 h 1 m 59 s 123 ms')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            2 * 60 * 60 * 1000 * 1000 * 1000, False),
            '2 h')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            3 * 24 * 60 * 60 * 1000 * 1000 * 1000 +
            2 * 60 * 60 * 1000 * 1000 * 1000 +
            60 * 1000 * 1000 * 1000 + 59 * 1000 * 1000 * 1000 +
            123 * 1000 * 1000, False),
            '2 h 1 m 59.123 s')
        self.assertEqual(_damo_fmt_str.format_time_ns(
            3 * 24 * 60 * 60 * 1000 * 1000 * 1000 +
            2 * 60 * 60 * 1000 * 1000 * 1000, False),
            '3 d 2 h')

    def test_text_to_time(self):
        self.assertEqual(_damo_fmt_str.text_to_us('1 us'), 1)
        self.assertEqual(_damo_fmt_str.text_to_us('1234 us'), 1234)
        self.assertEqual(_damo_fmt_str.text_to_us('1234us'), 1234)
        self.assertEqual(_damo_fmt_str.text_to_us('1 ms'), 1000)
        self.assertEqual(_damo_fmt_str.text_to_us('1 m 2 s'), 62 * 1000 * 1000)
        self.assertEqual(_damo_fmt_str.text_to_us('2 h 1 m 2 s'),
                7262 * 1000 * 1000)
        self.assertEqual(_damo_fmt_str.text_to_us('3 d 2 h 1 m 2 s'),
                3 * 24 * 60 * 1000 * 1000 +
                7262 * 1000 * 1000)

    def test_text_to_percent(self):
        self.assertEqual(_damo_fmt_str.text_to_percent('10%'), 10.0)
        self.assertEqual(_damo_fmt_str.text_to_percent('12.34%'), 12.34)
        self.assertEqual(_damo_fmt_str.text_to_percent('12.34 %'), 12.34)
        self.assertEqual(
                _damo_fmt_str.text_to_percent('1,234.567 %'), 1234.567)
        self.assertEqual(
                _damo_fmt_str.text_to_percent('1,234.567,89 %'), 1234.56789)

if __name__ == '__main__':
    unittest.main()
