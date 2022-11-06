#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json
import unittest

import _damon
import _damon_dbgfs
import _damon_sysfs

import _damo_schemes_input

class TestDamos(unittest.TestCase):
    def test_damo_schemes_to_damos(self):
        inputs = [
                # no comment
                '''
                [
                    {
                        "name": "0",
                        "action": "stat",
                        "access_pattern": {
                            "min_sz_bytes": 0,
                            "max_sz_bytes": 0,
                            "min_nr_accesses": 0,
                            "max_nr_accesses": 0,
                            "nr_accesses_unit": "sample_intervals",
                            "min_age": 0,
                            "max_age": 0,
                            "age_unit": "aggr_intervals"
                        },
                        "quotas": {
                            "time_ms": 0,
                            "sz_bytes": 0,
                            "reset_interval_ms": 0,
                            "weight_sz_permil": 0,
                            "weight_nr_accesses_permil": 0,
                            "weight_age_permil": 0
                        },
                        "watermarks": {
                            "metric": "none",
                            "interval_us": 0,
                            "high_permil": 0,
                            "mid_permil": 0,
                            "low_permil": 0
                        }
                    }
                ]
                ''',
                # with comments
                '''
                [
                    {
                        # some comment
                        "name": "0",
                        "action": "stat",
                        "access_pattern": {
                            "min_sz_bytes": 0,
                            "max_sz_bytes": 0,
                            "min_nr_accesses": 0,
                            "max_nr_accesses": 0,
                            "nr_accesses_unit": "sample_intervals",
                            "min_age": 0,
                            "max_age": 0,
                            "age_unit": "aggr_intervals"
                        },
                        "quotas": {
                            "time_ms": 0,
                            "sz_bytes": 0,
                            "reset_interval_ms": 0,
                            "weight_sz_permil": 0,
                            "weight_nr_accesses_permil": 0,
                            "weight_age_permil": 0
                        },
                        "watermarks": {
                            "metric": "none",
                            "interval_us": 0,
                            "high_permil": 0,
                            "mid_permil": 0,
                            "low_permil": 0
                        }
                    }
                ]
                ''',
                # human redable
                '''
                [
                    {
                        # some comment
                        "name": "0",
                        "action": "stat",
                        "access_pattern": {
                            "min_sz_bytes": "min",
                            "max_sz_bytes": "min",
                            "min_nr_accesses": 0,
                            "max_nr_accesses": 0,
                            "nr_accesses_unit": "sample_intervals",
                            "min_age": 0,
                            "max_age": 0,
                            "age_unit": "aggr_intervals"
                        },
                        "quotas": {
                            "time_ms": "0s",
                            "sz_bytes": "0B",
                            "reset_interval_ms": "0us",
                            "weight_sz_permil": 0,
                            "weight_nr_accesses_permil": 0,
                            "weight_age_permil": 0
                        },
                        "watermarks": {
                            "metric": "none",
                            "interval_us": "0us",
                            "high_permil": 0,
                            "mid_permil": 0,
                            "low_permil": 0
                        }
                    }
                ]
                ''',
        ]
        for txt in inputs:
            damos_list = _damo_schemes_input.damo_schemes_to_damos(txt)
            expected = _damon.Damos('0',
                        _damon.DamosAccessPattern(0, 0, 0, 0,
                            'sample_intervals', 0, 0, 'aggr_intervals'),
                        'stat',
                        _damon.DamosQuota(0, 0, 0, 0, 0, 0),
                        _damon.DamosWatermarks('none', 0, 0, 0, 0), None, None)
            self.assertEqual(damos_list[0], expected)

class TestDamon(unittest.TestCase):
    def test_kvpairs_transition(self):
        target = _damon.DamonTarget('foo', 1234, [_damon.DamonRegion(10, 20)])
        target_kvpairs = target.to_kvpairs()
        target_again = _damon.kvpairs_to_DamonTarget(target_kvpairs)
        self.assertEqual(target, target_again)

        damos = _damon.Damos('foo',
                _damon.DamosAccessPattern(0, 10, 5, 8, 'percent', 54, 88,
                    'usec'),
                'pageout',
                _damon.DamosQuota(100, 1024, 1000, 80, 76, 24),
                _damon.DamosWatermarks('free_mem_rate', 5000000, 800, 500,
                    200), None, None)
        damos_kvpairs = damos.to_kvpairs()
        damos_again = _damon.kvpairs_to_Damos(damos_kvpairs)
        self.assertEqual(damos, damos_again)

        ctx = _damon.DamonCtx('test_ctx',
                _damon.DamonIntervals(5000, 100000, 1000000),
                _damon.DamonNrRegionsRange(10, 1000),
                'paddr', [target], [damos])
        ctx_kvpairs = ctx.to_kvpairs()
        ctx_again = _damon.kvpairs_to_DamonCtx(ctx_kvpairs)
        self.assertEqual(ctx, ctx_again)


        kdamond = _damon.Kdamond('bar', 'off', 123, [ctx])
        kvpairs = kdamond.to_kvpairs()
        kdamond_again = _damon.kvpairs_to_Kdamond(kvpairs)
        self.assertEqual(kdamond, kdamond_again)

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
