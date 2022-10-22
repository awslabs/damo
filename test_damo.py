#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json
import unittest

import _damon_sysfs

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
        sysfs_dict = json.loads(sysfs_read_txt)['kdamonds']
        kdamonds = _damon_sysfs.files_content_to_kdamonds(sysfs_dict)
        wops = _damon_sysfs.wops_for_kdamonds(kdamonds)

        self.assertEqual(sysfs_dict, wops)

if __name__ == '__main__':
    unittest.main()
