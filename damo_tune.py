#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Update DAMON input parameters.
"""

import argparse

import _damon

def set_argparser(parser):
    _damon.set_monitoring_argparser(parser)
    parser.add_argument('--target', type=str, metavar='<target>',
            help='target pid or paddr')

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    err = _damon.initialize(args, skip_dirs_population=True)
    if err != None:
        print(err)
        exit(1)

    if _damon.damon_interface() == 'debugfs':
        print('tune does not support debugfs interface')
        exit(1)

    if not _damon.is_damon_running():
        print('DAMON is not turned on')
        exit(1)

    # TODO: Remove rbuf and out from the arguments in this case
    args.rbuf = 0
    args.out = 'null'
    attrs = _damon.cmd_args_to_attrs(args)
    init_regions = _damon.cmd_args_to_init_regions(args)

    if attrs.apply():
        print('attributes (%s) failed to be applied' % attrs)
    if args.target:
        if _damon.set_target(args.target, init_regions):
            print('target setting (%s, %s) failed' % (target, init_regions))
    if _damon.commit_inputs():
        print('could not commit inputs')


if __name__ == '__main__':
    main()
