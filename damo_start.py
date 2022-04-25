#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Start DAMON with given parameters.
"""

import argparse

import _damon

def set_argparser(parser):
    _damon.set_monitoring_argparser(parser)
    parser.add_argument('ops', choices=['vaddr', 'paddr', 'fvaddr'],
            default='vaddr',
            help='monitoring operations set')
    parser.add_argument('--target_pid', type=int, help='target pid')
    parser.add_argument('--numa_node', metavar='<node id>', type=int,
            help='limit the monitoring regions of the numa node')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    print(args)
    print('to be implemented...')

if __name__ == '__main__':
    main()
