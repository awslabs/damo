#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Stop DAMON.
"""

import argparse

import _damon

def set_argparser(parser):
    _damon.set_common_argparser(parser)
    return

def main(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    _damon.ensure_root_permission()
    _damon.ensure_initialized(args, True)

    any_kdamond_running = False
    for kd_name in _damon.current_kdamond_names():
        if _damon.is_kdamond_running(kd_name):
            any_kdamond_running = True
            break
    if not any_kdamond_running:
        print('DAMON is not turned on')
        exit(1)

    _damon.turn_damon('off', ['all'])

if __name__ == '__main__':
    main()
