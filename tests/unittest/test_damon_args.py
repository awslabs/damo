#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

import argparse
import os
import sys
import unittest

bindir = os.path.dirname(os.path.realpath(__file__))
damo_dir = os.path.join(bindir, '..', '..')
sys.path.append(damo_dir)

import _damon
import _damon_args

class TestDamonArgs(unittest.TestCase):
    def test_damon_ctx_from_damon_args(self):
        self.assertEqual(_damon_args.damon_ctx_from_damon_args(
            argparse.Namespace(**{'sample': '5000', 'aggr': '100000',
                'updr': '1000000', 'minr': 10, 'maxr': 1000,
                'regions': '123-456', 'numa_node': None, 'ops': 'paddr',
                'target_pid': None, 'schemes': None})),
            _damon.DamonCtx('0',
                _damon.DamonIntervals(5000, 100000, 1000000),
                _damon.DamonNrRegionsRange(10, 1000), 'paddr',
                [_damon.DamonTarget('0', None,
                    [_damon.DamonRegion(123, 456)])],
                []))

        self.assertEqual(_damon_args.damon_ctx_from_damon_args(
            argparse.Namespace(**{'sample': '5ms', 'aggr': '100ms',
                'updr': '1s', 'minr': '10', 'maxr': '1,000',
                'regions': '1K-4K', 'numa_node': None, 'ops': 'paddr',
                'target_pid': None, 'schemes': None})),
            _damon.DamonCtx('0',
                _damon.DamonIntervals(5000, 100000, 1000000),
                _damon.DamonNrRegionsRange(10, 1000), 'paddr',
                [_damon.DamonTarget('0', None,
                    [_damon.DamonRegion(1024, 4096)])],
                []))

if __name__ == '__main__':
    unittest.main()
