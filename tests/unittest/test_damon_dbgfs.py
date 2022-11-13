#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json
import os
import sys
import unittest

bindir = os.path.dirname(os.path.realpath(__file__))
damo_dir = os.path.join(bindir, '..', '..')
sys.path.append(damo_dir)

import _damon
import _damon_dbgfs

class TestDamonDbgfs(unittest.TestCase):
    def test_current_kdamond_names(self):
        self.assertEqual(_damon_dbgfs.current_kdamond_names(), ['0'])

    def test_debugfs_output_to_damos(self):
        _damon_dbgfs.feature_supports = {'init_regions': True, 'schemes': True,
                'schemes_stat_qt_exceed': True, 'init_regions_target_idx':
                True, 'schemes_prioritization': True, 'schemes_tried_regions':
                False, 'record': False, 'schemes_quotas': True, 'fvaddr':
                False, 'paddr': True, 'schemes_wmarks': True,
                'schemes_speed_limit': True, 'schemes_stat_succ': True,
                'vaddr': True}

        damos = _damon_dbgfs.debugfs_output_to_damos("4096 18446744073709551615 0 0 10 42949 5 0 584792941 1000 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
                _damon.DamonIntervals(5000, 100000, 1000000))
        expected = _damon.Damos('0',
                access_pattern=_damon.DamosAccessPattern(4096,
                    18446744073709551615, 0.0, 0.0, 'percent', 1000000.0,
                    4294900000.0, 'usec'),
                action='stat',
                quotas=_damon.DamosQuotas(time_ms=0, sz_bytes=584792941,
                    reset_interval_ms=1000, weight_sz_permil=0,
                    weight_nr_accesses_permil=0, weight_age_permil=0),
                watermarks=_damon.DamosWatermarks('none',0,0,0,0),
                stats=None)

        self.assertEqual(damos, expected)

    def test_files_content_to_kdamonds(self):
        _damon_dbgfs.feature_supports = {'init_regions': True, 'schemes': True,
                'schemes_stat_qt_exceed': True, 'init_regions_target_idx':
                True, 'schemes_prioritization': True, 'schemes_tried_regions':
                False, 'record': False, 'schemes_quotas': True, 'fvaddr':
                False, 'paddr': True, 'schemes_wmarks': True,
                'schemes_speed_limit': True, 'schemes_stat_succ': True,
                'vaddr': True}

        dbgfs_read_txts = [r'''
{
    "attrs": "5000 100000 1000000 10 1000\n",
    "init_regions": "0 1 100\n0 100 200\n",
    "kdamond_pid": "none\n",
    "mk_contexts": "read failed (reading /sys/kernel/debug/damon/mk_contexts failed ([Errno 22] Invalid argument))",
    "monitor_on": "off\n",
    "rm_contexts": "read failed (reading /sys/kernel/debug/damon/rm_contexts failed ([Errno 22] Invalid argument))",
    "schemes": "4096 18446744073709551615 0 0 10 42949 5 0 584792941 1000 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
    "target_ids": "4242\n"
}
''', r'''
{
    "attrs": "5000 100000 1000000 10 1000\n",
    "init_regions": "",
    "kdamond_pid": "none\n",
    "mk_contexts": "read failed (reading /sys/kernel/debug/damon/mk_contexts failed ([Errno 22] Invalid argument))",
    "monitor_on": "off\n",
    "rm_contexts": "read failed (reading /sys/kernel/debug/damon/rm_contexts failed ([Errno 22] Invalid argument))",
    "schemes": "4096 18446744073709551615 0 0 10 42949 5 0 5368709120 1000 0 3 7 1 1000000 999 998 995 0 0 0 0 0\n",
    "target_ids": "42\n"
}
''']

        expected_wops_list = [r'''
[{"/sys/kernel/debug/damon/attrs": "5000 100000 1000000 10 1000 "},
{"/sys/kernel/debug/damon/target_ids": "4242"},
{"/sys/kernel/debug/damon/init_regions": "0 1 100 0 100 200"},
{"/sys/kernel/debug/damon/schemes":
"4096\t18446744073709551615\t0\t0\t10\t42949\t5\t0\t584792941\t1000\t0\t0\t0\t0\t0\t0\t0\t0"}]
''', r'''
[{"/sys/kernel/debug/damon/attrs": "5000 100000 1000000 10 1000 "},
{"/sys/kernel/debug/damon/target_ids": "paddr\n"},
{"/sys/kernel/debug/damon/init_regions": ""},
{"/sys/kernel/debug/damon/schemes":
"4096\t18446744073709551615\t0\t0\t10\t42949\t5\t0\t5368709120\t1000\t0\t3\t7\t1\t1000000\t999\t998\t995"}]
''']

        for idx in range(len(dbgfs_read_txts)):
            dbgfs_read_txt = dbgfs_read_txts[idx]
            expected_wops = expected_wops_list[idx]
            dbgfs_dict = json.loads(dbgfs_read_txt)
            kdamonds = _damon_dbgfs.files_content_to_kdamonds(dbgfs_dict)
            wops = _damon_dbgfs.wops_for_kdamonds(kdamonds)
            self.assertEqual(json.loads(expected_wops), wops)

if __name__ == '__main__':
    unittest.main()
