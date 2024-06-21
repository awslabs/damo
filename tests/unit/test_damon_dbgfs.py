#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json
import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damo_fs
import _damon
import _damon_dbgfs

def set_damon_dbgfs_features():
    _damon_dbgfs.feature_supports = {'init_regions': True, 'schemes': True,
            'schemes_stat_qt_exceed': True, 'init_regions_target_idx': True,
            'schemes_prioritization': True, 'schemes_tried_regions': False,
            'record': False, 'schemes_quotas': True, 'fvaddr': False,
            'paddr': True, 'schemes_wmarks': True, 'schemes_speed_limit': True,
            'schemes_stat_succ': True, 'vaddr': True}

class TestDamonDbgfs(unittest.TestCase):
    def test_nr_kdamonds(self):
        self.assertEqual(_damon_dbgfs.nr_kdamonds(), 1)

    def test_debugfs_output_to_damos(self):
        set_damon_dbgfs_features()

        _test_damo_common.test_input_expects(self,
                lambda x: _damon_dbgfs.debugfs_output_to_damos(
                    x, _damon.DamonIntervals(5000, 100000, 1000000)),
                {"4096 18446744073709551615 0 0 10 42949 5 0 584792941 1000 0 0 0 0 0 0 0 0 0 0 0 0 0\n":
                    _damon.Damos(
                        access_pattern=_damon.DamosAccessPattern(
                            [4096, 18446744073709551615],
                            [0.0, 0.0], _damon.unit_percent,
                            [1000000.0, 4294900000.0], _damon.unit_usec),
                        action='stat', target_nid=None,
                        apply_interval_us=None,
                        quotas=_damon.DamosQuotas(time_ms=0,
                            sz_bytes=584792941, reset_interval_ms=1000,
                            weights=[0,0,0]),
                        watermarks=_damon.DamosWatermarks('none',0,0,0,0),
                        filters=[], stats=None)})

    def test_files_content_to_kdamonds_io(self):
        set_damon_dbgfs_features()

        _damo_fs.debug_dryrun({})
        kdamonds = _damon_dbgfs.files_content_to_kdamonds(json.loads(
            json.dumps(
                {
                    "attrs": "5000 100000 1000000 10 1000\n",
                    "init_regions": "0 1 100\n0 100 200\n",
                    "kdamond_pid": "none\n",
                    "mk_contexts":
                    "read failed (reading /sys/kernel/debug/damon/mk_contexts failed ([Errno 22] Invalid argument))",
                    "monitor_on": "off\n",
                    "rm_contexts":
                    "read failed (reading /sys/kernel/debug/damon/rm_contexts failed ([Errno 22] Invalid argument))",
                    "schemes":
                    "4096 18446744073709551615 0 0 10 42949 5 0 584792941 1000 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
                    "target_ids": "4242\n"
                    })))
        _damon_dbgfs.write_kdamonds('', kdamonds)

        kdamonds = _damon_dbgfs.files_content_to_kdamonds(json.loads(
            json.dumps(
                {
                    "attrs": "5000 100000 1000000 10 1000\n",
                    "init_regions": "",
                    "kdamond_pid": "none\n",
                    "mk_contexts":
                    "read failed (reading /sys/kernel/debug/damon/mk_contexts failed ([Errno 22] Invalid argument))",
                    "monitor_on": "off\n",
                    "rm_contexts":
                    "read failed (reading /sys/kernel/debug/damon/rm_contexts failed ([Errno 22] Invalid argument))",
                    "schemes":
                    "4096 18446744073709551615 0 0 10 42949 5 0 5368709120 1000 0 3 7 1 1000000 999 998 995 0 0 0 0 0\n",
                    "target_ids": "42\n"
                    })))
        _damon_dbgfs.write_kdamonds('', kdamonds)

        logs = _damo_fs.debug_get_dryrun_logs()
        expected_logs = [
                # First write_kdamonds()
                "write '5000 100000 1000000 10 1000' to 'attrs'",
                "write '4242' to 'target_ids'",
                "write '0 1 100 0 100 200' to 'init_regions'",
                "write '4096\t18446744073709551615\t0\t0\t10\t42949\t5\t0\t584792941\t1000\t0\t0\t0\t0\t0\t0\t0\t0' to 'schemes'",

                # Second write_kdamonds()
                "write '5000 100000 1000000 10 1000' to 'attrs'",
                "write 'paddr' to 'target_ids'",
                "write '' to 'init_regions'",
                "write '4096\t18446744073709551615\t0\t0\t10\t42949\t5\t0\t5368709120\t1000\t0\t3\t7\t1\t1000000\t999\t998\t995' to 'schemes'",
                ]
        self.assertEqual(expected_logs, logs)

if __name__ == '__main__':
    unittest.main()
