#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Start DAMON with given parameters.
"""

import argparse

import _damon
import _damo_paddr_layout

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

    _damon.ensure_root_permission()
    err = _damon.initialize(args)
    if err != None:
        print(err)
        exit(1)

    # TODO: Remove rbuf and out from the arguments in this case
    args.rbuf = 0
    args.out = 'null'
    attrs = _damon.cmd_args_to_attrs(args)
    init_regions = _damon.cmd_args_to_init_regions(args)
    numa_node = args.numa_node

    if args.ops == 'paddr':
        target = 'paddr'
        if not init_regions:
            if numa_node != None:
                init_regions = _damo_paddr_layout.paddr_region_of(numa_node)
            else:
                init_regions = [_damo_paddr_layout.default_paddr_region()]
    elif args.ops in ['vaddr', 'fvaddr']:
        try:
            pid = int(args.target_pid)
        except:
            print('target_pid (%s) is not an integer' % args.target_pid)
            exit(1)
        target = args.target_pid

    if attrs.apply():
        print('attributes (%s) failed to be applied' % attrs)
    if _damon.set_target(target, init_regions):
        print('target setting (%s, %s) failed' % (target, init_regions))
    if _damon.turn_damon('on'):
        print('could not turn on damon')
    while not _damon.is_damon_running():
        time.sleep(1)

if __name__ == '__main__':
    main()
