#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Start DAMON with given parameters.
"""

import argparse

import _damon
import _damo_paddr_layout

def set_argparser(parser):
    _damon.set_explicit_target_monitoring_argparser(parser)

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

    ctx = _damon.damon_ctx_from_damon_args(args)
    kdamonds = [_damon.Kdamond('0', [ctx])]
    _damon.apply_kdamonds(kdamonds)
    if _damon.turn_damon('on'):
        print('could not turn on damon')
    while not _damon.is_damon_running():
        time.sleep(1)

if __name__ == '__main__':
    main()
