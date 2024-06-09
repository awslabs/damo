#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import unittest

import _test_damo_common

_test_damo_common.add_damo_dir_to_syspath()

import _damo_fs
import _damon_sysfs

class TestDamonSysfs(unittest.TestCase):
    def test_json_kdamonds_staging(self):
        _damon_sysfs.feature_supports = {
                'fvaddr': True,
                'init_regions': True,
                'init_regions_target_idx': True,
                'paddr': True,
                'record': False,
                'schemes': True,
                'schemes_prioritization': True,
                'schemes_quotas': True,
                'schemes_quota_goals': True,
                'schemes_speed_limit': True,
                'schemes_tried_regions': True,
                'schemes_wmarks': True,
                'schemes_filters': True,
                'schemes_apply_interval': True,
                'vaddr': True}

        sysfs_dict = {
                "nr_kdamonds": "1\n",
                "0": {
                    "state": "off\n",
                    "pid": "-1\n",
                    "avail_state_inputs": '\n'.join(['on', 'off', 'commit',
                        'update_schemes_stats', 'update_schemes_tried_regions',
                        'clear_schemes_tried_regions\n']),
                    "contexts": {
                        "nr_contexts": "1\n",
                        "0": {
                            "avail_operations": "vaddr\nfvaddr\npaddr\n",
                            "operations": "paddr\n",
                            "monitoring_attrs": {
                                "intervals": {
                                    "sample_us": "5000\n",
                                    "update_us": "1000000\n",
                                    "aggr_us": "200000\n",
                                    },
                                "nr_regions": {
                                    "max": "1000\n", "min": "10\n"}
                                },
                            "targets": {"nr_targets": "0\n"},
                            "schemes": {
                                "nr_schemes": "1\n",
                                "0": {
                                    "access_pattern": {
                                        "age": {"max": "0\n", "min": "0\n"},
                                        "nr_accesses":
                                        {"max": "0\n", "min": "0\n"},
                                        "sz": {"max": "0\n", "min": "0\n"}},
                                    "action": "stat\n",
                                    "quotas": {
                                        "bytes": "0\n", "ms": "0\n",
                                        "reset_interval_ms": "0\n",
                                        "weights": {
                                            "age_permil": "0\n",
                                            "nr_accesses_permil": "0\n",
                                            "sz_permil": "0\n"
                                            }
                                        },
                                    "watermarks": {
                                        "metric": "none\n", "high": "0\n",
                                        "mid": "0\n", "low": "0\n",
                                        "interval_us": "0\n",
                                        },
                                    "stats": {
                                        "nr_applied": "0\n", "nr_tried": "0\n",
                                        "sz_applied": "0\n", "sz_tried": "0\n",
                                        "qt_exceeds": "0\n",
                                        },
                                    "tried_regions": {},
                                   },
                                },
                            },
                        },
                    }
                }
        expected_dryrun_log = [
                "read 'nr_kdamonds': '0'",
                "write '1' to 'nr_kdamonds'",
                "read '0/contexts/nr_contexts': '0'",
                "write '1' to '0/contexts/nr_contexts'",
                "write 'paddr' to '0/contexts/0/operations'",
                "write '5000' to '0/contexts/0/monitoring_attrs/intervals/sample_us'",
                "write '200000' to '0/contexts/0/monitoring_attrs/intervals/aggr_us'",
                "write '1000000' to '0/contexts/0/monitoring_attrs/intervals/update_us'",
                "write '10' to '0/contexts/0/monitoring_attrs/nr_regions/min'",
                "write '1000' to '0/contexts/0/monitoring_attrs/nr_regions/max'",
                "read '0/contexts/0/targets/nr_targets': '0'",
                "read '0/contexts/0/schemes/nr_schemes': '0'",
                "write '1' to '0/contexts/0/schemes/nr_schemes'",
                "write '0' to '0/contexts/0/schemes/0/access_pattern/sz/min'",
                "write '0' to '0/contexts/0/schemes/0/access_pattern/sz/max'",
                "write '0' to '0/contexts/0/schemes/0/access_pattern/nr_accesses/min'",
                "write '0' to '0/contexts/0/schemes/0/access_pattern/nr_accesses/max'",
                "write '0' to '0/contexts/0/schemes/0/access_pattern/age/min'",
                "write '0' to '0/contexts/0/schemes/0/access_pattern/age/max'",
                "write 'stat' to '0/contexts/0/schemes/0/action'",
                "write '0' to '0/contexts/0/schemes/0/quotas/ms'",
                "write '0' to '0/contexts/0/schemes/0/quotas/bytes'",
                "write '0' to '0/contexts/0/schemes/0/quotas/reset_interval_ms'",
                "write '0' to '0/contexts/0/schemes/0/quotas/weights/sz_permil'",
                "write '0' to '0/contexts/0/schemes/0/quotas/weights/nr_accesses_permil'",
                "write '0' to '0/contexts/0/schemes/0/quotas/weights/age_permil'",
                "write 'none' to '0/contexts/0/schemes/0/watermarks/metric'",
                "write '0' to '0/contexts/0/schemes/0/watermarks/interval_us'",
                "write '0' to '0/contexts/0/schemes/0/watermarks/high'",
                "write '0' to '0/contexts/0/schemes/0/watermarks/mid'",
                "write '0' to '0/contexts/0/schemes/0/watermarks/low'",
                ]

        _damo_fs.debug_dryrun(
                {
                    'nr_kdamonds': '0',
                    '0/contexts/nr_contexts': '0',
                    '0/contexts/0/targets/nr_targets': '0',
                    '0/contexts/0/schemes/nr_schemes': '0',
                    })
        kdamonds = _damon_sysfs.files_content_to_kdamonds(sysfs_dict)
        _damon_sysfs.write_kdamonds_dir('', kdamonds)
        logs = _damo_fs.debug_get_dryrun_logs()
        self.assertEqual(expected_dryrun_log, logs)

if __name__ == '__main__':
    unittest.main()
