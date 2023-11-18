#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damo_fmt_str

class TestDamoFmtStr(unittest.TestCase):
    def test_format_nr(self):
        self.assertEqual(_damo_fmt_str.format_nr(123, False), '123')
        self.assertEqual(_damo_fmt_str.format_nr(1234, False), '1,234')
        self.assertEqual(_damo_fmt_str.format_nr(1234567, False), '1,234,567')

    def test_text_to_nr(self):
        _test_damo_common.test_input_expects(self,
                _damo_fmt_str.text_to_nr,
                {
                    '12': 12,
                    '1,234': 1234,
                    '1,234.567': 1234.567,
                    '1,234,567': 1234567,
                    '1,234.567': 1234.567,
                    123: 123,
                    0.123: 0.123,
                    })

    def test_format_time(self):
        usec_ns = 1000
        msec_ns = 1000 * usec_ns
        sec_ns = 1000 * msec_ns
        minute_ns = 60 * sec_ns
        hour_ns = 60 * minute_ns
        day_ns = 24 * hour_ns
        _test_damo_common.test_input_expects_funcs(self,
                [lambda x: _damo_fmt_str.format_time_ns_exact(x, False),
                    lambda x: _damo_fmt_str.format_time_ns(x, False)],
                {
                    123: ['123 ns', '123 ns'],
                    123456: ['123 us 456 ns', '123.456 us'],
                    123000: ['123 us', '123 us'],
                    123456789: ['123 ms 456 us 789 ns', '123.457 ms'],
                    123000000: ['123 ms', '123 ms'],
                    123456789123:
                    ['2 m 3 s 456 ms 789 us 123 ns', '2 m 3.457 s'],
                    123000000000: ['2 m 3 s', '2 m 3 s'],
                    1 * minute_ns: ['1 m', '1 m'],
                    1 * minute_ns + 59 * sec_ns: ['1 m 59 s', '1 m 59 s'],
                    1 * minute_ns + 59 * sec_ns + 123 * msec_ns:
                    ['1 m 59 s 123 ms', '1 m 59.123 s'],
                    2 * hour_ns + 1 * minute_ns + 59 * sec_ns + 123 * msec_ns:
                    ['2 h 1 m 59 s 123 ms', '2 h 1 m 59.123 s'],
                    2 * hour_ns: ['2 h', '2 h'],
                    3 * day_ns + 2 * hour_ns + 1 * minute_ns +
                    59 * sec_ns + 123 * msec_ns:
                    ['3 d 2 h 1 m 59 s 123 ms', '74 h 1 m 59.123 s'],
                    3 * day_ns + 2 * hour_ns: ['3 d 2 h', '74 h'],
                    1234 * day_ns + 2 * hour_ns: ['1,234 d 2 h', '29618 h'],
                    _damo_fmt_str.ulong_max: ['max', 'max'],
                    })

        for input_ in [123, 1234, 12345, 123456]:
            for func in [_damo_fmt_str.format_time_us,
                    _damo_fmt_str.format_time_ms]:
                self.assertEqual(func(input_, True), '%s' % input_)

    def test_format_ratio(self):
        _test_damo_common.test_input_expects(self,
                lambda x: _damo_fmt_str.format_ratio(x, False),
                {
                    123: '12,300 %',
                    123.1230001: '12,312.30001 %',
                    0.1: '10 %',
                    0.001: '0.1 %',
                    0.0001: '0.01 %',
                    0.00001: '0.001 %',
                    0.000001: '0.0001 %',
                    0.000000001: '0.0000001 %',
                    0.0000000001: '0 %',
                    })

    def test_format_permil(self):
        _test_damo_common.test_input_expects(self,
                lambda x: _damo_fmt_str.format_permil(x, False),
                {
                    123000: '12,300 %',
                    123123.0001: '12,312.30001 %',
                    100: '10 %',
                    1: '0.1 %',
                    0.1: '0.01 %',
                    0.01: '0.001 %',
                    0.001: '0.0001 %',
                    0.000001: '0.0000001 %',
                    0.0000001: '0 %',
                    })

    def test_format_bp(self):
        _test_damo_common.test_input_expects(self,
                lambda x: _damo_fmt_str.format_bp(x, False),
                {
                    123000: '1,230 %',
                    123123.0001: '1,231.230001 %',
                    100: '1 %',
                    1: '0.01 %',
                    0.1: '0.001 %',
                    0.01: '0.0001 %',
                    0.001: '0.00001 %',
                    0.000001: '0 %',
                    0.0000001: '0 %',
                    })

    def test_text_to_time(self):
        _test_damo_common.test_input_expects(self,
                _damo_fmt_str.text_to_ns,
                {
                    '1': 1,
                    '1 ns': 1,
                    'max': _damo_fmt_str.ulong_max,
                    '123.456': 123.456,
                    123: 123,
                    123.456: 123.456,
                    })
        _test_damo_common.test_input_expects(self,
                _damo_fmt_str.text_to_us,
                {
                    '1 us': 1,
                    '1234 us': 1234,
                    '1,234 us': 1234,
                    '1234us': 1234,
                    '1 ms': 1000,
                    '1 m 2 s': 62 * 1000 * 1000,
                    '2 h 1 m 2 s': 7262 * 1000 * 1000,
                    '3 d 2 h 1 m 2 s':
                    3 * 24 * 60 * 60 * 1000 * 1000 + 7262 * 1000 * 1000,
                    '134': 134,
                    'max': _damo_fmt_str.ulong_max,
                    '123': 123,
                    '123.456': 123.456,
                    123: 123,
                    123.456: 123.456,
                    })
        _test_damo_common.test_input_expects(self,
                _damo_fmt_str.text_to_ms,
                {
                    '134': 134,
                    'max': _damo_fmt_str.ulong_max,
                    '123': 123,
                    '123.456': 123.456,
                    123: 123,
                    123.456: 123.456,
                    })
        _test_damo_common.test_input_expects(self,
                _damo_fmt_str.text_to_sec,
                {
                    '134': 134,
                    'max': _damo_fmt_str.ulong_max,
                    '123': 123,
                    '123.456': 123.456,
                    123: 123,
                    123.456: 123.456,
                    })

    def test_text_to_percent(self):
        _test_damo_common.test_input_expects(self,
                _damo_fmt_str.text_to_percent,
                {'10%': 10.0,
                    12.34: 12.34,
                    '12.34': 12.34,
                    '12.34%': 12.34,
                    '12.34 %': 12.34,
                    '1,234.567 %': 1234.567,
                    '1,234.567,89 %': 1234.56789,
                    '1,234': 1234,
                    '123': 123,
                    '123.456': 123.456,
                    123: 123,
                    123.456: 123.456,
                    })

    def test_text_to_permil(self):
        _test_damo_common.test_input_expects(self,
                _damo_fmt_str.text_to_permil,
                {'10%': 100.0,
                    12.34: 12.34,
                    '12.34': 12.34,
                    '1.234%': 12.34,
                    '1.234 %': 12.34,
                    '1,234.567 %': 12345.67,
                    '1,234.567,89 %': 12345.6789,
                    '123': 123,
                    '123.456': 123.456,
                    123: 123,
                    123.456: 123.456,
                    })

    def test_text_to_bp(self):
        _test_damo_common.test_input_expects(self,
                _damo_fmt_str.text_to_bp,
                {'10%': 1000.0,
                    12.34: 12.34,
                    '12.34': 12.34,
                    '1.234%': 123.4,
                    '1.234 %': 123.4,
                    '1,234.567 %': 123456.7,
                    '1,234.567,89 %': 123456.789,
                    '123': 123,
                    '123.456': 123.456,
                    123: 123,
                    123.456: 123.456,
                    })

    def test_text_to_ratio(self):
        _test_damo_common.test_input_expects(self,
                _damo_fmt_str.text_to_ratio,
                {'10%': 0.1,
                    '12.34%': 0.1234,
                    '200%': 2.0,
                    0.5: 0.5,
                    '1,234.567 %': 12.34567,
                    '1,234.56': 1234.56,
                    '123': 123,
                    '123.456': 123.456,
                    123: 123,
                    123.456: 123.456,
                    })

    def test_text_to_bytes(self):
        _test_damo_common.test_input_expects(self, _damo_fmt_str.text_to_bytes,
                {
                    '123': 123,
                    '1,234': 1234,
                    '123 B': 123,
                    '2 K': 2048,
                    '2 KB': 2048,
                    '2 KiB': 2048,
                    '2 M': 2 * 1 << 20,
                    '2 MB': 2 * 1 << 20,
                    '2 MiB': 2 * 1 << 20,
                    '2 G': 2 * 1 << 30,
                    '2 GB': 2 * 1 << 30,
                    '1,234.457 G': int(1234.457 * (1 << 30)),
                    '1,234.457 GiB': int(1234.457 * (1 << 30)),
                    '1,234.457': 1234.457,
                    '2 GiB': 2 * 1 << 30,
                    '2 T': 2 * 1 << 40,
                    '2 TB': 2 * 1 << 40,
                    '2 TiB': 2 * 1 << 40,
                    '2 P': 2 * 1 << 50,
                    '2 PB': 2 * 1 << 50,
                    '2 PiB': 2 * 1 << 50,
                    '2.0 PiB': 2 * 1 << 50,
                    '16384.000 PiB': (1 << 64) - 1,
                    '2.0 EiB': 2 * 1 << 60,
                    '2.0 EB': 2 * 1 << 60,
                    '123': 123,
                    '123.456': 123.456,
                    123: 123,
                    123.456: 123.456,
                    })

    def test_text_to_bool(self):
        _test_damo_common.test_input_expects(self, _damo_fmt_str.text_to_bool,
                {
                    True: True,
                    False: False,
                    'Y': True,
                    'y': True,
                    'YES': True,
                    'yes': True,
                    'Yes': True,
                    'TRUE': True,
                    'true': True,
                    'True': True,
                    'N': False,
                    'n': False,
                    'NO': False,
                    'No': False,
                    'FALSE': False,
                    'false': False,
                    'False': False,
                    })

if __name__ == '__main__':
    unittest.main()
