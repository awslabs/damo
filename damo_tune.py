#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Update DAMON input parameters.
"""

import argparse

import _damon

def set_argparser(parser):
    _damon.set_explicit_target_monitoring_argparser(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    _damon.ensure_initialized(args, True)

    if _damon.damon_interface() == 'debugfs':
        print('tune does not support debugfs interface')
        exit(1)

    if not _damon.is_damon_running():
        print('DAMON is not turned on')
        exit(1)

    ctx = _damon.damon_ctx_from_damon_args(args)
    kdamonds = [_damon.Kdamond('0', [ctx])]
    _damon.apply_kdamonds(kdamonds)
    if _damon.commit_inputs():
        print('could not commit inputs')

if __name__ == '__main__':
    main()
