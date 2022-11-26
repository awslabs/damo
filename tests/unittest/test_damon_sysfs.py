#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import json
import os
import sys
import unittest

bindir = os.path.dirname(os.path.realpath(__file__))
damo_dir = os.path.join(bindir, '..', '..')
sys.path.append(damo_dir)

import _damon_sysfs

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
                'schemes_filters': True,
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
                            },
                            "filters": {
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
