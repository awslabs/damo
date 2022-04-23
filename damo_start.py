#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0

"""
Start DAMON with given parameters.
"""

import argparse

import _damon

def set_argparser(parser):
    _damon.set_monitoring_argparser(parser)

def amin(args=None):
    if not args:
        parser = argparse.ArgumentParser()
        set_argparser(parser)
        args = parser.parse_args()

    print(args)
    print('to be implemented...')

if __name__ == '__main__':
    main()
