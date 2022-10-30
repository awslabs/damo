#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json
import unittest

import _damon
import _damon_dbgfs
import _damon_sysfs

class TestDamon(unittest.TestCase):
    def test_damos_eq(self):
        damos = _damon.Damos('0',
                access_pattern=_damon.DamosAccessPattern(4096,
                    18446744073709551615, 0.0, 0.0, 'percent', 1000000,
                    4294900000, 'usec'),
                action='stat',
                quotas=_damon.DamosQuota(time_ms=0, sz_bytes=584792941,
                    reset_interval_ms=1000, weight_sz_permil=0,
                    weight_nr_accesses_permil=0, weight_age_permil=0),
                watermarks=_damon.DamosWatermarks(0,0,0,0,0),
                stats=None)
        self.assertEqual(damos, damos)

class TestDamonDbgfs(unittest.TestCase):
    def test_debugfs_output_to_damos(self):
        damos = _damon_dbgfs.debugfs_output_to_damos("4096 18446744073709551615 0 0 10 42949 5 0 584792941 1000 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
                _damon.DamonIntervals(5000, 100000, 1000000))
        expected = _damon.Damos('0',
                access_pattern=_damon.DamosAccessPattern(4096,
                    18446744073709551615, 0.0, 0.0, 'percent', 1000000.0,
                    4294900000.0, 'usec'),
                action='stat',
                quotas=_damon.DamosQuota(time_ms=0, sz_bytes=584792941,
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

class TestDamonSysfs(unittest.TestCase):
    def test_json_kdamonds_convert(self):
        _damon_sysfs.feature_supports = {
                'fvaddr': True,
                'init_regions': True,
                'init_regions_target_idx': True,
                'paddr': True,
                'record': False,
                'schemes': True,
                'schemes_prioritization': True,
                'schemes_quotas': True,
                'schemes_speed_limit': True,
                'schemes_tried_regions': True,
                'schemes_wmarks': True,
                'vaddr': True}

        sysfs_read_txt = r'''
{
    "kdamonds": {
        "0": {
            "avail_state_inputs": "on\noff\ncommit\nupdate_schemes_stats\nupdate_schemes_tried_regions\nclear_schemes_tried_regions\n", 
            "contexts": {
                "0": {
                    "avail_operations": "vaddr\nfvaddr\npaddr\n", 
                    "monitoring_attrs": {
                        "intervals": {
                            "aggr_us": "200000\n", 
                            "sample_us": "5000\n", 
                            "update_us": "1000000\n"
                        }, 
                        "nr_regions": {
                            "max": "1000\n", 
                            "min": "10\n"
                        }
                    }, 
                    "operations": "paddr\n", 
                    "schemes": {
                        "0": {
                            "access_pattern": {
                                "age": {
                                    "max": "0\n", 
                                    "min": "0\n"
                                }, 
                                "nr_accesses": {
                                    "max": "0\n", 
                                    "min": "0\n"
                                }, 
                                "sz": {
                                    "max": "0\n", 
                                    "min": "0\n"
                                }
                            }, 
                            "action": "stat\n", 
                            "quotas": {
                                "bytes": "0\n", 
                                "ms": "0\n", 
                                "reset_interval_ms": "0\n", 
                                "weights": {
                                    "age_permil": "0\n", 
                                    "nr_accesses_permil": "0\n", 
                                    "sz_permil": "0\n"
                                }
                            }, 
                            "stats": {
                                "nr_applied": "0\n", 
                                "nr_tried": "0\n", 
                                "qt_exceeds": "0\n", 
                                "sz_applied": "0\n", 
                                "sz_tried": "0\n"
                            }, 
                            "tried_regions": {}, 
                            "watermarks": {
                                "high": "0\n", 
                                "interval_us": "0\n", 
                                "low": "0\n", 
                                "metric": "none\n", 
                                "mid": "0\n"
                            }
                        }, 
                        "nr_schemes": "1\n"
                    }, 
                    "targets": {
                        "nr_targets": "0\n"
                    }
                }, 
                "nr_contexts": "1\n"
            }, 
            "pid": "-1\n", 
            "state": "off\n"
        }, 
        "nr_kdamonds": "1\n"
    }
}
'''

        expected_wops = r'''
{
    "0": {
        "contexts": {
            "0": [
                {
                    "operations": "paddr"
                },
                {
                    "monitoring_attrs": {
                        "intervals": {
                            "aggr_us": "200000",
                            "sample_us": "5000",
                            "update_us": "1000000"
                        },
                        "nr_regions": {
                            "max": "1000",
                            "min": "10"
                        }
                    }
                },
                {
                    "targets": {}
                },
                {
                    "schemes": {
                        "0": {
                            "access_pattern": {
                                "age": {
                                    "max": "0",
                                    "min": "0"
                                },
                                "nr_accesses": {
                                    "max": "0",
                                    "min": "0"
                                },
                                "sz": {
                                    "max": "0",
                                    "min": "0"
                                }
                            },
                            "action": "stat",
                            "quotas": {
                                "bytes": "0",
                                "ms": "0",
                                "reset_interval_ms": "0",
                                "weights": {
                                    "age_permil": "0",
                                    "nr_accesses_permil": "0",
                                    "sz_permil": "0"
                                }
                            },
                            "watermarks": {
                                "high": "0",
                                "interval_us": "0",
                                "low": "0",
                                "metric": "none",
                                "mid": "0"
                            }
                        }
                    }
                }
            ]
        }
    }
}
'''

        sysfs_dict = json.loads(sysfs_read_txt)['kdamonds']
        kdamonds = _damon_sysfs.files_content_to_kdamonds(sysfs_dict)
        wops = _damon_sysfs.wops_for_kdamonds(kdamonds)
        self.assertEqual(json.loads(expected_wops), wops)

if __name__ == '__main__':
    unittest.main()
