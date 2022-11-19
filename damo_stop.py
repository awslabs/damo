#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Stop DAMON.
"""

import argparse

import _damon
import _damon_args

def set_argparser(parser):
    _damon_args.set_common_argparser(parser)
    return

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    _damon.ensure_initialized(args)

    if _damon.every_kdamond_turned_off():
        print('DAMON is not turned on')
        exit(1)

    _damon.turn_damon('off', _damon.current_kdamond_names())

if __name__ == '__main__':
    main()
