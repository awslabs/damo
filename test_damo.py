#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json
import unittest

import _damon_dbgfs
import _damon_sysfs

class TestDamonDbgfs(unittest.TestCase):
    def test_files_content_to_kdamonds(self):
        dbgfs_read_txt = r'''

{
    "attrs": "5000 100000 1000000 10 1000\n",
    "init_regions": "0 1 100\n0 100 200\n1 20 40\n1 50 100\n",
    "kdamond_pid": "none\n",
    "mk_contexts": "read failed (reading /sys/kernel/debug/damon/mk_contexts failed ([Errno 22] Invalid argument))",
    "monitor_on": "off\n",
    "rm_contexts": "read failed (reading /sys/kernel/debug/damon/rm_contexts failed ([Errno 22] Invalid argument))",
    "schemes": "4096 18446744073709551615 0 0 10 42949 5 0 584792941 1000 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
    "target_ids": "4242 4243\n"
}
'''
        expected_wops = r'''
{
    "attrs": "5000 100000 1000000 10 1000\n",
    "init_regions": "0 1 100 0 100 200 1 20 40 1 50 100\n",
    "schemes": "4096 18446744073709551615 0 0 10 42949 5 0 584792941 1000 0 0 0 0 0 0 0 0 0 0 0 0 0\n",
    "target_ids": "4242 4243\n"
}
'''
	dbgfs_dict = json.loads(dbgfs_read_txt)
        kdamonds = _damon_dbgfs.files_content_to_kdamonds(dbgfs_dict)
        wops = _damon_dbgfs.wops_for_kdamonds(kdamonds)
        self.assertEqual(json.loads(expected_wops), wops)

class TestDamonSysfs(unittest.TestCase):
    def test_json_kdamonds_convert(self):
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
                            "action": "stat\n",
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
