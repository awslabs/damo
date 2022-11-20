#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Start DAMON with given parameters.
"""

import argparse

import _damon
import _damon_args
import _damo_paddr_layout

def set_argparser(parser):
    _damon_args.set_explicit_target_argparser(parser)

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    err = _damon.ensure_initialized(args)
    if err != None:
        print(err)
        exit(1)

    err, ctx = _damon_args.turn_explicit_args_damon_on(args)
    if err:
        print('could not turn on damon')

if __name__ == '__main__':
    main()
