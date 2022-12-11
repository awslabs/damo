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
        self.assertEqual(_damo_fmt_str.text_to_nr('1,234.567'), 1234.567)
        self.assertEqual(_damo_fmt_str.text_to_nr('1,234,567'), 1234567)

    def test_format_time(self):
        usec_ns = 1000
        msec_ns = 1000 * usec_ns
        sec_ns = 1000 * msec_ns
        minute_ns = 60 * sec_ns
        hour_ns = 60 * minute_ns
        day_ns = 24 * hour_ns
        inputs = [
                123,
                123456,
                123000,
                123456789,
                123000000,
                123456789123,
                123000000000,
                1 * minute_ns,
                1 * minute_ns + 59 * sec_ns,
                1 * minute_ns + 59 * sec_ns + 123 * msec_ns,
                2 * hour_ns + 1 * minute_ns + 59 * sec_ns + 123 * msec_ns,
                2 * hour_ns,
                3 * day_ns + 2 * hour_ns + 1 * minute_ns + 59 * sec_ns + 123 *
                msec_ns,
                3 * day_ns + 2 * hour_ns,
                1234 * day_ns + 2 * hour_ns]
        expects_exacts = [
                '123 ns',
                '123 us 456 ns',
                '123 us',
                '123 ms 456 us 789 ns',
                '123 ms',
                '2 m 3 s 456 ms 789 us 123 ns',
                '2 m 3 s',
                '1 m',
                '1 m 59 s',
                '1 m 59 s 123 ms',
                '2 h 1 m 59 s 123 ms',
                '2 h',
                '3 d 2 h 1 m 59 s 123 ms',
                '3 d 2 h',
                '1,234 d 2 h',]
        expects = [
                '123 ns',
                '123.456 us',
                '123 us',
                '123.457 ms',
                '123 ms',
                '2 m 3.457 s',
                '2 m 3 s',
                '1 m',
                '1 m 59 s',
                '1 m 59.123 s',
                '2 h 1 m 59.123 s',
                '2 h',
                '74 h 1 m 59.123 s',
                '74 h',
                '29618 h',]

        for idx, ns in enumerate(inputs):
            self.assertEqual(_damo_fmt_str.format_time_ns_exact(ns, False),
                    expects_exacts[idx])
            self.assertEqual(_damo_fmt_str.format_time_ns(ns, False),
                    expects[idx])

    def test_text_to_time(self):
        self.assertEqual(_damo_fmt_str.text_to_ns('1 ns'), 1)
        self.assertEqual(_damo_fmt_str.text_to_us('1 us'), 1)
        self.assertEqual(_damo_fmt_str.text_to_us('1234 us'), 1234)
        self.assertEqual(_damo_fmt_str.text_to_us('1,234 us'), 1234)
        self.assertEqual(_damo_fmt_str.text_to_us('1234us'), 1234)
        self.assertEqual(_damo_fmt_str.text_to_us('1 ms'), 1000)
        self.assertEqual(_damo_fmt_str.text_to_us('1 m 2 s'), 62 * 1000 * 1000)
        self.assertEqual(_damo_fmt_str.text_to_us('2 h 1 m 2 s'),
                7262 * 1000 * 1000)
        self.assertEqual(_damo_fmt_str.text_to_us('3 d 2 h 1 m 2 s'),
                3 * 24 * 60 * 60 * 1000 * 1000 +
                7262 * 1000 * 1000)

    def test_text_to_percent(self):
        self.assertEqual(_damo_fmt_str.text_to_percent('10%'), 10.0)
        self.assertEqual(_damo_fmt_str.text_to_percent('12.34%'), 12.34)
        self.assertEqual(_damo_fmt_str.text_to_percent('12.34 %'), 12.34)
        self.assertEqual(
                _damo_fmt_str.text_to_percent('1,234.567 %'), 1234.567)
        self.assertEqual(
                _damo_fmt_str.text_to_percent('1,234.567,89 %'), 1234.56789)

    def test_text_to_bytes(self):
        self.assertEqual(_damo_fmt_str.text_to_bytes('123'), 123)
        self.assertEqual(_damo_fmt_str.text_to_bytes('123 B'), 123)
        self.assertEqual(_damo_fmt_str.text_to_bytes('2 K'), 2048)
        self.assertEqual(_damo_fmt_str.text_to_bytes('2 KiB'), 2048)
        self.assertEqual(_damo_fmt_str.text_to_bytes('2 M'), 2 * 1 << 20)
        self.assertEqual(_damo_fmt_str.text_to_bytes('2 MiB'), 2 * 1 << 20)
        self.assertEqual(_damo_fmt_str.text_to_bytes('2 G'), 2 * 1 << 30)
        self.assertEqual(_damo_fmt_str.text_to_bytes('2 GiB'), 2 * 1 << 30)
        self.assertEqual(_damo_fmt_str.text_to_bytes('2 T'), 2 * 1 << 40)
        self.assertEqual(_damo_fmt_str.text_to_bytes('2 TiB'), 2 * 1 << 40)

if __name__ == '__main__':
    unittest.main()
